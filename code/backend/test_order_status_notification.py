"""Case and regression checks for the order status lookup in AD06 and UC06."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import os
import re
import uuid
from unittest import TestCase, skipUnless
from unittest.mock import patch

import mysql.connector

from app import create_app
from domain.errors import DomainError, NotFoundError
from repositories.order_status_notification_repository import OrderStatusNotificationRepository
from services.order_status_notification_service import OrderStatusNotificationService


class Cursor:
    def __init__(self, order, lines, search_rows):
        self.order, self.lines, self.search_rows = order, list(lines), list(search_rows)
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.statements.append((sql, params))

    def fetchone(self):
        return self.order

    def fetchall(self):
        return self.lines if "FROM Bestelregel" in self.statements[-1][0] else self.search_rows


class Connection:
    """Only SELECT is available; accidental database writes are rejected by the fake."""

    def __init__(self, order=None, lines=(), search_rows=()):
        self.cur = Cursor(order, lines, search_rows)

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


class OrderStatusNotificationTests(TestCase):
    def setUp(self):
        self.order = {
            "bestelling_id": 12,
            "besteld_op": datetime(2026, 10, 28, 14, 5),
            "gewenste_leverdatum": date(2026, 10, 31),
            "dagdeel": "ochtend",
            "status_naam": "backorder",
            "bedrijfsnaam": "Apotheek De Linde",
        }
        self.lines = [
            {"artikelnummer": "T-1", "productnaam": "Paracetamol", "aantal": 10,
             "prijs_per_eenheid": Decimal("5.20"), "afnemen_bij_tekort": 1,
             "aantal_afgeleverd": 2, "gereserveerd": 0,
             "in_open_deelorder": 0, "in_afgeronde_deelorder": 0, "in_open_levering": 0},
            {"artikelnummer": "T-2", "productnaam": "Ibuprofen", "aantal": 5,
             "prijs_per_eenheid": Decimal("12.00"), "afnemen_bij_tekort": 0,
             "aantal_afgeleverd": 0, "gereserveerd": 5,
             "in_open_deelorder": 0, "in_afgeronde_deelorder": 0, "in_open_levering": 0},
            {"artikelnummer": "T-3", "productnaam": "Vitamine C", "aantal": 3,
             "prijs_per_eenheid": Decimal("3.99"), "afnemen_bij_tekort": None,
             "aantal_afgeleverd": 0, "gereserveerd": 0,
             "in_open_deelorder": 0, "in_afgeronde_deelorder": 0, "in_open_levering": 0},
        ]

    def service(self, connection):
        return OrderStatusNotificationService(OrderStatusNotificationRepository(connection))

    def test_search_by_customer_name_and_order_number(self):
        connection = Connection(search_rows=[self.order])
        results = self.service(connection).search("  Linde ")
        self.assertEqual(connection.cur.statements[0][1], (None, "%Linde%"))
        self.assertEqual(results[0]["status_label"], "Backorder")
        results = self.service(connection).search("12")
        self.assertEqual(connection.cur.statements[1][1], (12, "%12%"))
        self.assertEqual(results[0]["bestelling_id"], 12)

    def test_search_escapes_wildcards_and_avoids_out_of_range_integer(self):
        conn = Connection(search_rows=[self.order])
        self.service(conn).search("AB_%!")
        self.assertEqual(conn.cur.statements[0][1], (None, "%AB!_!%!!%"))
        self.assertIn("ESCAPE '!'", conn.cur.statements[0][0])
        self.service(conn).search("9" * 100)
        self.assertIsNone(conn.cur.statements[1][1][0])

    def test_empty_and_oversized_search_never_queries(self):
        conn = Connection()
        self.assertEqual(self.service(conn).search("   "), [])
        with self.assertRaises(DomainError):
            self.service(conn).search("x" * 101)
        self.assertFalse(conn.cur.statements)

    def test_reject_invalid_order_numbers_without_query(self):
        for value in ("x", None, 0, -3, True, 1.5, 2**31):
            conn = Connection(order=self.order)
            with self.subTest(value=value), self.assertRaises(DomainError):
                self.service(conn).status_overview(value)
            self.assertFalse(conn.cur.statements)

    def test_order_not_found_does_not_read_lines(self):
        conn = Connection()
        with self.assertRaises(NotFoundError):
            self.service(conn).status_overview(99)
        self.assertEqual(len(conn.cur.statements), 1)

    def test_known_missing_and_unknown_statuses(self):
        for value, label, tone in (
            ("wordt verzameld", "Wordt verzameld", "info"),
            ("verstuurd", "Verstuurd", "info"),
            ("backorder", "Backorder", "warning"),
            ("afgeleverd", "Afgeleverd", "success"),
            ("niet afgeleverd", "niet afgeleverd", "neutral"),
            (None, "Niet geregistreerd", "neutral"),
        ):
            conn = Connection(order={**self.order, "status_naam": value})
            with self.subTest(value=value):
                result = self.service(conn).status_overview(12)
                self.assertEqual(result["order"]["status_label"], label)
                self.assertEqual(result["order"]["status_tone"], tone)
                self.assertEqual(result["has_backorder"], value == "backorder")

    def test_shortage_choice_is_historical_not_live_stock(self):
        result = self.service(Connection(self.order, self.lines)).status_overview(12)
        self.assertEqual(result["has_backorder"], True)
        self.assertEqual(len(result["shortage_lines"]), 1)
        self.assertEqual(len(result["undelivered_shortages"]), 1)
        self.assertEqual(result["shortage_lines"][0]["artikelnummer"], "T-1")
        self.assertEqual(result["lines"][0]["proces_label"],
                         "Deels afgeleverd, geen vervolgstap geregistreerd")
        self.assertEqual(result["lines"][1]["proces_label"],
                         "Voorraad voor deze bestelling gereserveerd")
        self.assertNotIn("backorder_lines", result)
        self.assertNotIn("resterend_backorderaantal", result["lines"][0])

    def test_process_steps_are_separate_from_shortage_choice(self):
        examples = (
            ("gereserveerd", 4, "Voorraad voor deze bestelling gereserveerd"),
            ("in_open_deelorder", 4, "Deelorder aangemaakt, nog niet afgerond"),
            ("in_afgeronde_deelorder", 4, "Deelorder afgerond, aflevering niet bevestigd"),
            ("in_open_levering", 4, "Levering geregistreerd, ontvangst niet bevestigd"),
            ("aantal_afgeleverd", 10, "Volledig afgeleverd"),
            ("aantal_afgeleverd", 11, "Afgeleverde hoeveelheid controleren"),
        )
        for field, quantity, expected in examples:
            row = {**self.lines[0], "aantal_afgeleverd": 0, field: quantity}
            result = self.service(Connection(self.order, [row])).status_overview(12)
            with self.subTest(field=field):
                self.assertEqual(result["lines"][0]["proces_label"], expected)
                self.assertEqual(len(result["shortage_lines"]), 1)

    def test_advanced_processing_wins_over_prior_reservation(self):
        row = {**self.lines[0], "gereserveerd": 10, "in_open_deelorder": 10,
               "in_afgeronde_deelorder": 10, "in_open_levering": 10}
        result = self.service(Connection(self.order, [row])).status_overview(12)
        self.assertEqual(result["lines"][0]["proces_label"],
                         "Levering geregistreerd, ontvangst niet bevestigd")

    def test_multiple_shortage_agreements_and_current_order_status(self):
        rows = [self.lines[0], {**self.lines[1], "afnemen_bij_tekort": True},
                self.lines[2]]
        result = self.service(Connection(self.order, rows)).status_overview(12)
        self.assertEqual([x["artikelnummer"] for x in result["shortage_lines"]],
                         ["T-1", "T-2"])
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, rows)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("2 producten", page)
        self.assertIn("Geregistreerde backorderafspraken", page)
        self.assertIn("Paracetamol (T-1): Deels afgeleverd", page)
        self.assertIn("Ibuprofen (T-2): Voorraad voor deze bestelling gereserveerd", page)
        self.assertNotIn("Vitamine C (T-3):", page)
        self.assertNotIn("producten in backorder", page.lower())

    def test_delivered_shortage_remains_history_not_current_backorder(self):
        row = {**self.lines[0], "aantal_afgeleverd": 10, "in_open_levering": 0}
        result = self.service(Connection(self.order, [row])).status_overview(12)
        self.assertEqual(result["shortage_lines"][0]["proces_label"], "Volledig afgeleverd")
        self.assertEqual(result["undelivered_shortages"], [])
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, [row])):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("Paracetamol (T-1): Volledig afgeleverd", page)
        self.assertIn("algemene orderstatus staat nog op backorder", page)

    def test_shortage_agreement_visible_when_order_no_longer_backorder(self):
        order = {**self.order, "status_naam": "verstuurd"}
        result = self.service(Connection(order, self.lines)).status_overview(12)
        self.assertFalse(result["has_backorder"])
        self.assertEqual(len(result["shortage_lines"]), 1)
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(order, self.lines)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("Geregistreerde backorderafspraken", page)
        self.assertNotIn("algemene orderstatus staat nog op backorder", page)
        self.assertIn("Dit is een vastgelegde afspraak", page)

    def test_backorder_order_without_shortage_lines_is_not_assigned_to_products(self):
        rows = [{**row, "afnemen_bij_tekort": None} for row in self.lines]
        result = self.service(Connection(self.order, rows)).status_overview(12)
        self.assertTrue(result["has_backorder"])
        self.assertEqual(result["shortage_lines"], [])
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, rows)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("Productregistratie ontbreekt", page)
        self.assertIn("geen tekortafspraak per product geregistreerd", page)
        self.assertNotIn("Paracetamol (T-1):", page)

    def test_all_queries_read_only_and_documented_sql_matches(self):
        conn = Connection(self.order, self.lines, [self.order])
        self.service(conn).search("12")
        self.service(conn).status_overview(12)
        for query, _ in conn.cur.statements:
            self.assertTrue(query.strip().startswith("SELECT"))
            self.assertNotIn("UPDATE ", query.upper())
            self.assertNotIn("INSERT ", query.upper())
            self.assertNotIn("DELETE ", query.upper())
        self.assertEqual(len(conn.cur.statements), 3)
        sql_document = (Path(__file__).parents[1] / "database" / "queries.sql").read_text(encoding="utf-8")
        pr_queries = sql_document.split("-- PR #97: zoeken op ordernummer of klantnaam")[1]
        documented = re.findall(r"^SELECT\s+.*?;", pr_queries, re.DOTALL | re.MULTILINE)
        self.assertEqual(len(documented), 3)
        for (query, params), statement in zip(conn.cur.statements, documented):
            rendered = query
            for value in params:
                rendered = rendered.replace("%s", f"'{value}'" if isinstance(value, str) else str(value), 1)
            normalize = lambda text: " ".join(text.split())
            self.assertEqual(normalize(rendered) + ";", normalize(statement))

    def test_detail_renders_recorded_information_only(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, self.lines)):
                response = client.get("/orders/12/status")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        for expected in (
            "Order 12", "Backorderafspraken bij bestelling", "1 product",
            "31-10-2026, ochtend", "Geregistreerde backorderafspraken",
            "Paracetamol (T-1): Deels afgeleverd", "Ibuprofen", "Vitamine C",
            "Ja, bij tekort afnemen", "Nee, bij tekort niet afnemen",
            "Niet geregistreerd", "Bevestigd afgeleverd", "Geregistreerde voortgang",
            "Voorraad voor deze bestelling gereserveerd",
            "order-status-notification.css",
        ):
            self.assertIn(expected, page)
        self.assertNotIn("Backorder: 6", page)
        self.assertNotIn("Bericht voor de klant", page)
        self.assertNotIn("In backorder, aflevering niet compleet", page)

    def test_search_page_reuses_main_sales_and_handles_empty_results(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(search_rows=[self.order])):
                response = client.get("/orders?order=Linde")
            self.assertEqual(response.status_code, 200)
            page = response.get_data(as_text=True)
            for expected in ("/orders/12/status", "Apotheek De Linde", "Voorraad controleren",
                             "Korting berekenen", "Orderstatus opzoeken"):
                self.assertIn(expected, page)
            with patch("routes.sales.get_connection", return_value=Connection()):
                self.assertIn("Geen order gevonden.", client.get("/orders?order=Onbekend").get_data(as_text=True))
                self.assertEqual(client.get("/orders/99/status").status_code, 404)

    def test_main_order_overview_and_pr97_detail_have_distinct_endpoints(self):
        routes = {rule.rule: rule.endpoint for rule in create_app().url_map.iter_rules()}
        self.assertEqual(routes["/orders/status"], "sales.order_status")
        self.assertEqual(
            routes["/orders/<int:order_id>/status"], "sales.order_status_detail"
        )

    def test_idle_sales_page_does_not_connect_to_database(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", side_effect=AssertionError("No DB needed")):
                response = client.get("/orders")
            self.assertEqual(response.status_code, 200)


@skipUnless(
    os.getenv("TIMAFLU_TEST_ALLOW_RESET") == "isolated"
    and os.getenv("TIMAFLU_TEST_MYSQL_HOST") == "127.0.0.1",
    "Requires an explicitly isolated MySQL service.",
)
class OrderStatusMySQLIntegrationTests(TestCase):
    def test_real_mysql_backorders_exclude_confirmed_deliveries(self):
        """AD05/AD06: accepted shortages remain until a delivery is confirmed.

        A planned delivery does not count. Multiple attempts for one delivery
        are counted once. No production database is opened or modified.
        """
        options = {
            "host": "127.0.0.1",
            "port": int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
            "user": os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
            "password": os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        }
        name = "timaflu_pr97_" + uuid.uuid4().hex[:12]
        admin = mysql.connector.connect(**options)
        connection = None
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE `{name}`")
            admin.commit()
            connection = mysql.connector.connect(database=name, **options)
            schema = (Path(__file__).parents[1] / "database" / "schema.sql").read_text(
                encoding="utf-8"
            )
            sql = "\n".join(
                line for line in schema.splitlines()
                if not line.lstrip().startswith("--")
            )
            with connection.cursor() as cursor:
                for statement in sql.split(";"):
                    if statement.strip():
                        cursor.execute(statement)

                cursor.execute("INSERT INTO Adres (adres) VALUES ('TEST adres')")
                address_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Klant (bedrijfsnaam, afleveradres_id, betaaladres_id)
                       VALUES ('TEST apotheek', %s, %s)""",
                    (address_id, address_id),
                )
                customer_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Bestelling (klant_id, afleveradres_id, betaaladres_id,
                       besteld_op, gewenste_leverdatum, dagdeel, status_naam)
                       VALUES (%s, %s, %s, '2026-10-28', '2026-10-31',
                               'ochtend', 'backorder')""",
                    (customer_id, address_id, address_id),
                )
                order_id = cursor.lastrowid
                products = {}
                for article, quantity, choice in (
                    ("T-1", 10, 1),  # Delivered after two delivery attempts.
                    ("T-2", 10, 1),  # Partly delivered; remaining in open delivery.
                    ("T-3", 5, None),  # Allocated stock, no shortage choice.
                    ("T-4", 8, 1),  # Reserved, no delivery yet.
                    ("T-5", 8, 1),  # Robot assignment still open.
                    ("T-6", 8, 1),  # Completed robot assignment.
                    ("T-7", 8, 1),  # Shortage agreement, no further records.
                ):
                    cursor.execute(
                        """INSERT INTO Product (artikelnummer, bestelcode, productnaam,
                           prijs_per_grootverpakking, aantal_detailverpakkingen,
                           minimale_bestelhoeveelheid, minimumvoorraad)
                           VALUES (%s, %s, %s, 10, 1, 1, 0)""",
                        (article, article + "-CODE", article),
                    )
                    product_id = cursor.lastrowid
                    products[article] = product_id
                    cursor.execute(
                        """INSERT INTO Bestelregel (bestelling_id, product_id, aantal,
                           prijs_per_eenheid, afnemen_bij_tekort)
                           VALUES (%s, %s, %s, 10, %s)""",
                        (order_id, product_id, quantity, choice),
                    )
                for article in ("T-3", "T-4"):
                    cursor.execute(
                        """INSERT INTO Voorraadreservering
                           (bestelling_id, product_id, aantal) VALUES (%s, %s, %s)""",
                        (order_id, products[article], 5 if article == "T-3" else 8),
                    )
                cursor.execute(
                    "INSERT INTO Robot (robot_id, gang) VALUES (1, 'A'), (2, 'B')"
                )
                for article, robot_id, completed in (
                    ("T-5", 1, False), ("T-6", 2, True)
                ):
                    cursor.execute(
                        """INSERT INTO Deelorder (bestelling_id, robot_id, afgerond)
                           VALUES (%s, %s, %s)""",
                        (order_id, robot_id, completed),
                    )
                    suborder_id = cursor.lastrowid
                    cursor.execute(
                        """INSERT INTO Deelorderregel (deelorder_id, product_id, aantal)
                           VALUES (%s, %s, 8)""",
                        (suborder_id, products[article]),
                    )
                cursor.execute(
                    "INSERT INTO Koerier (naam, beschikbaar) VALUES ('TEST koerier', TRUE)"
                )
                courier_id = cursor.lastrowid
                cursor.execute(
                    "INSERT INTO Rit (koerier_id, ritdatum) VALUES (%s, '2026-10-31')",
                    (courier_id,),
                )
                trip_id = cursor.lastrowid

                def delivery(article, count, outcomes):
                    cursor.execute(
                        "INSERT INTO Levering (bestelling_id) VALUES (%s)", (order_id,)
                    )
                    delivery_id = cursor.lastrowid
                    cursor.execute(
                        """INSERT INTO Leveringregel (levering_id, product_id,
                           aantal_geleverd) VALUES (%s, %s, %s)""",
                        (delivery_id, products[article], count),
                    )
                    for number, outcome in enumerate(outcomes, start=1):
                        cursor.execute(
                            """INSERT INTO Leverpoging (levering_id, pogingnummer,
                               rit_id, geplande_tijd, resultaat, ontvangst_getekend)
                               VALUES (%s, %s, %s, '10:00:00', %s, %s)""",
                            (delivery_id, number, trip_id, outcome,
                             outcome == "afgeleverd"),
                        )

                delivery("T-1", 10, ["niet aanwezig", "afgeleverd"])
                delivery("T-2", 4, ["afgeleverd"])
                delivery("T-2", 6, [None])
            connection.commit()

            service = OrderStatusNotificationService(
                OrderStatusNotificationRepository(connection)
            )
            result = service.status_overview(order_id)
            lines = {line["artikelnummer"]: line for line in result["lines"]}
            self.assertEqual(lines["T-1"]["aantal_afgeleverd"], 10)
            self.assertEqual(lines["T-2"]["aantal_afgeleverd"], 4)
            self.assertEqual(lines["T-2"]["in_open_levering"], 6)
            self.assertEqual(lines["T-3"]["gereserveerd"], 5)
            self.assertEqual(lines["T-4"]["gereserveerd"], 8)
            self.assertEqual(lines["T-5"]["in_open_deelorder"], 8)
            self.assertEqual(lines["T-6"]["in_afgeronde_deelorder"], 8)
            self.assertEqual(
                [line["artikelnummer"] for line in result["shortage_lines"]],
                ["T-1", "T-2", "T-4", "T-5", "T-6", "T-7"],
            )
            self.assertEqual(
                [line["artikelnummer"] for line in result["undelivered_shortages"]],
                ["T-2", "T-4", "T-5", "T-6", "T-7"],
            )
            for article, expected in (
                ("T-1", "Volledig afgeleverd"),
                ("T-2", "Levering geregistreerd, ontvangst niet bevestigd"),
                ("T-3", "Voorraad voor deze bestelling gereserveerd"),
                ("T-4", "Voorraad voor deze bestelling gereserveerd"),
                ("T-5", "Deelorder aangemaakt, nog niet afgerond"),
                ("T-6", "Deelorder afgerond, aflevering niet bevestigd"),
                ("T-7", "Geen reservering of verdere verwerking geregistreerd"),
            ):
                with self.subTest(article=article):
                    self.assertEqual(lines[article]["proces_label"], expected)
            app = create_app()
            app.testing = True
            with app.test_client() as client:
                with patch("routes.sales.get_connection", return_value=connection):
                    page = client.get(f"/orders/{order_id}/status")
            self.assertEqual(page.status_code, 200)
            html = page.get_data(as_text=True)
            self.assertIn("T-2 (T-2): Levering geregistreerd", html)
            self.assertIn("T-1 (T-1): Volledig afgeleverd", html)
            self.assertNotIn("In backorder, aflevering niet compleet", html)
        finally:
            if connection is not None:
                connection.close()
            try:
                with admin.cursor() as cursor:
                    cursor.execute(f"DROP DATABASE IF EXISTS `{name}`")
                admin.commit()
            finally:
                admin.close()
