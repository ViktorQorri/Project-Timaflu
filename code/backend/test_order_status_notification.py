"""Case and regression checks for the order status lookup in AD06 and UC06."""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
import re
from unittest import TestCase
from unittest.mock import patch

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
             "aantal_afgeleverd": 2},
            {"artikelnummer": "T-2", "productnaam": "Ibuprofen", "aantal": 5,
             "prijs_per_eenheid": Decimal("12.00"), "afnemen_bij_tekort": 0,
             "aantal_afgeleverd": 0},
            {"artikelnummer": "T-3", "productnaam": "Vitamine C", "aantal": 3,
             "prijs_per_eenheid": Decimal("3.99"), "afnemen_bij_tekort": None,
             "aantal_afgeleverd": 0},
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

    def test_shortage_choices_are_not_misrepresented_as_open_quantities(self):
        result = self.service(Connection(self.order, self.lines)).status_overview("12")
        self.assertEqual(result["lines"], self.lines)
        self.assertEqual([x["afnemen_bij_tekort"] for x in result["lines"]], [1, 0, None])
        self.assertEqual(result["backorder_lines"], [self.lines[0]])
        self.assertNotIn("message", result)
        self.assertTrue(result["has_backorder"])

    def test_multiple_backorder_products_use_recorded_shortage_choices(self):
        lines = [self.lines[0], {**self.lines[1], "afnemen_bij_tekort": True},
                 self.lines[2]]
        result = self.service(Connection(self.order, lines)).status_overview(12)
        self.assertEqual([line["artikelnummer"] for line in result["backorder_lines"]],
                         ["T-1", "T-2"])
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, lines)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("2 geregistreerde backorderregels", page)
        self.assertIn("<li>Paracetamol (T-1)</li>", page)
        self.assertIn("<li>Ibuprofen (T-2)</li>", page)
        self.assertNotIn("<li>Vitamine C (T-3)</li>", page)

    def test_fully_delivered_line_not_shown_as_outstanding(self):
        lines = [{**self.lines[0], "aantal_afgeleverd": 10},
                 {**self.lines[1], "afnemen_bij_tekort": True,
                  "aantal_afgeleverd": 2},
                 self.lines[2]]
        result = self.service(Connection(self.order, lines)).status_overview(12)
        self.assertEqual([line["artikelnummer"] for line in result["backorder_lines"]],
                         ["T-2"])
        self.assertEqual(len(result["accepted_backorder_lines"]), 2)
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection",
                       return_value=Connection(self.order, lines)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("<li>Ibuprofen (T-2)</li>", page)
        self.assertNotIn("<li>Paracetamol (T-1)</li>", page)
        self.assertIn("Aflevering bevestigd, orderstatus controleren", page)

    def test_all_accepted_lines_delivered_does_not_invent_backorder(self):
        lines = [{**self.lines[0], "aantal_afgeleverd": 10},
                 self.lines[1], self.lines[2]]
        result = self.service(Connection(self.order, lines)).status_overview(12)
        self.assertTrue(result["has_backorder"])
        self.assertEqual(result["backorder_lines"], [])
        self.assertEqual(len(result["accepted_backorder_lines"]), 1)
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection",
                       return_value=Connection(self.order, lines)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("Status controleren", page)
        self.assertIn("volledig afgeleverd", page)
        self.assertNotIn("<li>Paracetamol (T-1)</li>", page)

    def test_historical_shortage_is_not_presented_as_current_backorder(self):
        delivered_order = {**self.order, "status_naam": "afgeleverd"}
        result = self.service(Connection(delivered_order, self.lines)).status_overview(12)
        self.assertFalse(result["has_backorder"])
        self.assertEqual(result["backorder_lines"], [])
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection",
                       return_value=Connection(delivered_order, self.lines)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("Tekortafspraak geregistreerd", page)
        self.assertNotIn("Producten in backorder", page)
        self.assertNotIn('>In backorder</span>', page)

    def test_order_backorder_without_marked_lines_reports_missing_registration(self):
        lines = [{**line, "afnemen_bij_tekort": None} for line in self.lines]
        result = self.service(Connection(self.order, lines)).status_overview(12)
        self.assertTrue(result["has_backorder"])
        self.assertEqual(result["backorder_lines"], [])
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection",
                       return_value=Connection(self.order, lines)):
                page = client.get("/orders/12/status").get_data(as_text=True)
        self.assertIn("Producten niet geregistreerd", page)
        self.assertIn("geen afzonderlijke producten als backorder vastgelegd", page)
        self.assertNotIn("<li>Paracetamol", page)

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
            for expected in ("Order 12", "1 geregistreerde backorderregel",
                             "31-10-2026, ochtend", "Producten in backorder",
                             "<li>Paracetamol (T-1)</li>", "In backorder",
                             "Ibuprofen", "Vitamine C", "€ 5,20", "€ 3,99",
                             "Backorder per product", "Geen tekortkeuze vastgelegd",
                             "Niet afnemen bij tekort"):
                self.assertIn(expected, page)
            self.assertNotIn("<li>Ibuprofen (T-2)</li>", page)
            self.assertNotIn("Backorder: 6", page)
            self.assertNotIn("Bericht voor de klant", page)
            self.assertNotIn("Afgeleverd op", page)
            self.assertIn("order-status-notification.css", page)

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

    def test_idle_sales_page_does_not_connect_to_database(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", side_effect=AssertionError("No DB needed")):
                response = client.get("/orders")
            self.assertEqual(response.status_code, 200)
