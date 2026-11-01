"""Casuscontrole AD06: zoeken, selecteren, orderregels en echte orderstatussen.

Mocks voor HTML en SQL-contract. Echte MySQL-verificatie gebeurt afzonderlijk
tegen een wegwerpdatabase; deze tests schrijven niets weg.
"""

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from repositories.order_status_report_repository import OrderStatusReportRepository

DATABASE = Path(__file__).resolve().parents[1] / "database" / "queries.sql"


def order(number, status, customer="Apotheek De Linde", urgent=False):
    return {
        "bestelling_id": number,
        "bedrijfsnaam": customer,
        "besteld_op": datetime(2026, 10, 12, 9, 30),
        "gewenste_leverdatum": date(2026, 10, 14),
        "dagdeel": "ochtend",
        "spoed": urgent,
        "status_naam": status,
    }


def line(product_id=1, choice=True, name="Testmedicijn"):
    return {
        "product_id": product_id,
        "artikelnummer": "TST-001",
        "productnaam": name,
        "aantal": 3,
        "prijs_per_eenheid": Decimal("12.50"),
        "afnemen_bij_tekort": choice,
    }


class Cursor:
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=()):
        self.connection.calls.append((sql, params))
        if "FROM Bestelregel" in sql:
            self.rows = self.connection.lines
        elif "WHERE b.bestelling_id = %s" in sql:
            self.rows = [self.connection.detail_order] if self.connection.detail_order else []
        elif "k.bedrijfsnaam LIKE" in sql:
            self.rows = self.connection.search_rows
        else:
            self.rows = self.connection.orders

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None


class Connection:
    def __init__(self, orders=(), search_rows=None, detail_order=None, lines=()):
        self.orders = list(orders)
        self.search_rows = list(search_rows) if search_rows is not None else list(orders)
        self.detail_order = detail_order
        self.lines = list(lines)
        self.calls = []

    def cursor(self, dictionary=False):
        assert dictionary
        return Cursor(self)


class OrderStatusReportTests(TestCase):
    def setUp(self):
        self.orders = [
            order(1, "wordt verzameld"),
            order(2, "verstuurd"),
            order(3, "backorder", "Apotheek Oost"),
            order(4, "afgeleverd", "Apotheek Noord"),
            order(5, "niet afgeleverd", urgent=True),
            order(6, None),
        ]

    def get(self, url, connection):
        app = create_app()
        app.testing = True
        with patch("routes.reports.get_connection", return_value=connection):
            with app.test_client() as client:
                response = client.get(url)
        return response

    def test_overview_uses_read_only_existing_tables_and_original_status_values(self):
        conn = Connection(orders=self.orders)
        result = OrderStatusReportRepository(conn).list_orders()
        self.assertEqual(result, self.orders)
        query, params = conn.calls[0]
        for required in ("JOIN Klant", "b.status_naam", "b.besteld_op",
                         "b.gewenste_leverdatum", "b.dagdeel", "ORDER BY"):
            self.assertIn(required, query)
        for forbidden in ("WHERE", "INSERT", "UPDATE", "DELETE", "Bestelregel"):
            self.assertNotIn(forbidden.upper(), query.upper())
        self.assertEqual(params, ())

    def test_numeric_search_uses_parameterized_exact_order_id_and_customer_name(self):
        conn = Connection(search_rows=[self.orders[3]])
        rows = OrderStatusReportRepository(conn).search_orders("4")
        self.assertEqual(rows, [self.orders[3]])
        sql, params = conn.calls[0]
        self.assertIn("b.bestelling_id = %s", sql)
        self.assertIn("k.bedrijfsnaam LIKE %s ESCAPE '!'", sql)
        self.assertEqual(params, (4, "%4%"))
        self.assertNotIn("= 4", sql)

    def test_customer_name_search_accepts_literal_wildcards(self):
        conn = Connection(search_rows=[self.orders[0]])
        repo = OrderStatusReportRepository(conn)
        repo.search_orders("Apotheek")
        self.assertEqual(conn.calls[0][1], (None, "%Apotheek%"))
        repo.search_orders("Zorg%_! BV")
        self.assertEqual(conn.calls[1][1], (None, "%Zorg!%!_!! BV%"))
        self.assertNotIn("Zorg", conn.calls[1][0])

    def test_large_numeric_search_does_not_make_unbounded_integer_conversion(self):
        conn = Connection(search_rows=[])
        OrderStatusReportRepository(conn).search_orders("9" * 120)
        self.assertEqual(conn.calls[0][1][0], None)

    def test_detail_queries_are_read_only_and_use_existing_order_line_columns(self):
        conn = Connection(detail_order=self.orders[2], lines=[line()])
        repo = OrderStatusReportRepository(conn)
        self.assertEqual(repo.find_order(3), self.orders[2])
        self.assertEqual(repo.list_order_lines(3), [line()])
        self.assertEqual(len(conn.calls), 2)
        self.assertEqual(conn.calls[0][1], (3,))
        self.assertEqual(conn.calls[1][1], (3,))
        self.assertIn("br.afnemen_bij_tekort", conn.calls[1][0])
        self.assertIn("JOIN Product", conn.calls[1][0])
        self.assertNotIn("Voorraadreservering", conn.calls[1][0])
        for query, _ in conn.calls:
            self.assertNotIn("INSERT", query.upper())
            self.assertNotIn("UPDATE", query.upper())

    def test_all_four_queries_match_the_sql_deliverable(self):
        text = DATABASE.read_text(encoding="utf-8")
        norm = lambda value: " ".join(value.strip().rstrip(";").split()).lower()

        conn = Connection(orders=[], detail_order=None, lines=[])
        repo = OrderStatusReportRepository(conn)
        repo.list_orders()
        repo.search_orders("Apotheek")
        repo.find_order(1)
        repo.list_order_lines(1)

        examples = (
            text.split("-- Order status overview for GET /reports", 1)[1],
            text.split("-- AD06 search by exact order number", 1)[1],
            text.split("-- AD06 select one order:", 1)[1],
            text.split("-- AD06 order lines and recorded shortage acceptance:", 1)[1],
        )
        queries = []
        for example in examples:
            queries.append("SELECT " + example.split("\nSELECT ", 1)[1].split(";", 1)[0])
        # The documented example parameters differ only by their literals.
        queries[1] = queries[1].replace("= NULL", "= %s").replace("LIKE '%Apotheek%'", "LIKE %s")
        queries[2] = queries[2].replace("= 1", "= %s")
        queries[3] = queries[3].replace("= 1", "= %s")
        self.assertEqual([norm(sql) for sql, _ in conn.calls], [norm(sql) for sql in queries])

    def test_overview_has_selectable_orders_and_status_labels(self):
        resp = self.get("/reports", Connection(orders=self.orders))
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for value in ("Wordt verzameld", "Verstuurd", "Backorder", "Afgeleverd",
                      "Niet afgeleverd", "Nog geen status", "Spoed",
                      "Apotheek Noord", "14-10-2026"):
            self.assertIn(value, html)
        self.assertIn('href="/reports/3"', html)
        self.assertIn('name="order"', html)
        self.assertIn('tabindex="0"', html)
        self.assertNotIn("Openstaande orders", html)
        self.assertNotIn('name="from"', html)

    def test_search_shows_matching_orders_and_preserves_query(self):
        conn = Connection(orders=self.orders, search_rows=[self.orders[2]])
        resp = self.get("/reports?order=Oost", conn)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Apotheek Oost", html)
        self.assertNotIn("Apotheek Noord", html)
        self.assertIn('value="Oost"', html)
        self.assertEqual(len(conn.calls), 1)
        self.assertEqual(conn.calls[0][1], (None, "%Oost%"))

    def test_no_matches_returns_not_found_message(self):
        resp = self.get("/reports?order=Onbekende", Connection(search_rows=[]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Geen order gevonden.", resp.get_data(as_text=True))

    def test_empty_overview_shows_empty_state_not_fake_statistics(self):
        resp = self.get("/reports", Connection())
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Geen bestellingen gevonden.", resp.get_data(as_text=True))

    def test_detail_shows_saved_lines_delivery_time_and_backorder_choice(self):
        conn = Connection(detail_order=self.orders[2], lines=[
            line(choice=True),
            line(2, False, "Ander medicijn"),
            line(3, None, "Zonder keuze"),
        ])
        resp = self.get("/reports/3", conn)
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        for value in ("Bestelling 3", "Backorderinformatie", "14-10-2026",
                      "Testmedicijn", "TST-001", "12,50",
                      "Geaccepteerd", "Niet geaccepteerd", "Niet vastgelegd",
                      "Het exacte ontbrekende aantal"):
            self.assertIn(value, html)
        self.assertNotIn("Gereserveerd", html)
        self.assertEqual([params for _, params in conn.calls], [(3,), (3,)])

    def test_other_status_has_no_false_backorder_claim(self):
        resp = self.get("/reports/4", Connection(detail_order=self.orders[3], lines=[line()]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Deze bestelling heeft geen backorderstatus.", resp.get_data(as_text=True))

    def test_null_status_and_missing_order_lines_are_explicit(self):
        resp = self.get("/reports/6", Connection(detail_order=self.orders[5], lines=[]))
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)
        self.assertIn("Nog geen status", html)
        self.assertIn("Geen bestelregels geregistreerd.", html)

    def test_unknown_order_returns_404_without_fabricated_details(self):
        conn = Connection(detail_order=None)
        resp = self.get("/reports/999", conn)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Geen order gevonden.", resp.get_data(as_text=True))
        self.assertEqual(len(conn.calls), 1)

    def test_zero_and_negative_order_identifiers_are_not_valid_routes(self):
        for url in ("/reports/0", "/reports/-1", "/reports/niet-numeriek"):
            resp = self.get(url, Connection())
            # Flask rejects negative and text values; zero is not a stored ID.
            self.assertIn(resp.status_code, (404,))

    def test_escaping_customer_and_medication_names(self):
        entry = order(8, "backorder", "<script>alert(1)</script>")
        conn = Connection(orders=[entry], detail_order=entry,
                          lines=[line(name="<script>alert(2)</script>")])
        for page in ("/reports", "/reports/8"):
            resp = self.get(page, conn)
            self.assertEqual(resp.status_code, 200)
            html = resp.get_data(as_text=True)
            self.assertNotIn("<script>alert", html)
            self.assertIn("&lt;script&gt;", html)

    def test_lookup_does_not_modify_the_existing_sales_stock_search(self):
        app = create_app()
        source = app.jinja_loader.get_source(app.jinja_env, "orders.html")[0]
        self.assertIn('url_for(\'reports.index\')', source)
        self.assertIn('name="q"', source)
        self.assertIn('name="quantity"', source)
