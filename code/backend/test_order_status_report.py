"""Case checks for the read-only order status overview; no live DB required."""

from datetime import date, datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from repositories.order_status_report_repository import OrderStatusReportRepository

DATABASE = Path(__file__).resolve().parents[1] / "database" / "queries.sql"


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql):
        self.sql = sql

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.cur = Cursor(rows)

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


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


class OrderStatusReportTests(TestCase):
    def setUp(self):
        self.rows = [
            order(1, "wordt verzameld"),
            order(2, "verstuurd"),
            order(3, "backorder", "Apotheek Oost"),
            order(4, "afgeleverd", "Apotheek Noord"),
            order(5, "niet afgeleverd", urgent=True),
            order(6, None),
        ]

    def test_repository_reads_status_with_customer_and_delivery(self):
        connection = Connection(self.rows)
        rows = OrderStatusReportRepository(connection).list_orders()
        self.assertEqual(rows, self.rows)
        for term in ("JOIN Klant", "b.besteld_op", "b.gewenste_leverdatum",
                     "b.dagdeel", "b.status_naam", "ORDER BY"):
            self.assertIn(term, connection.cur.sql)
        self.assertNotIn("Bestelregel", connection.cur.sql)
        self.assertNotIn("WHERE", connection.cur.sql.upper())
        self.assertNotIn("%s", connection.cur.sql)

    def test_documented_sql_is_identical_to_application_query(self):
        repo=OrderStatusReportRepository(Connection([]))
        repo.list_orders()
        source=repo.connection.cur.sql.strip()
        documented=DATABASE.read_text(encoding="utf-8").split(
            "-- Order status overview for GET /reports",1
        )[1].split("SELECT ",1)[1].split(";",1)[0]
        normalize=lambda value: " ".join(value.split()).lower()
        self.assertEqual(normalize(source), normalize("SELECT " + documented))

    def test_page_shows_real_status_values_without_invented_groups(self):
        app=create_app()
        app.testing=True
        with patch("routes.reports.get_connection", return_value=Connection(self.rows)):
            with app.test_client() as client:
                response=client.get("/reports")
        self.assertEqual(response.status_code, 200)
        html=response.get_data(as_text=True)
        for word in ("Wordt verzameld", "Verstuurd", "Backorder", "Afgeleverd",
                     "Niet afgeleverd", "Nog geen status", "Spoed",
                     "Apotheek Noord", "14-10-2026"):
            self.assertIn(word, html)
        self.assertIn('tabindex="0"', html)
        self.assertIn('role="region"', html)
        self.assertNotIn("Openstaande orders", html)
        self.assertNotIn("orders in deze periode", html)
        self.assertNotIn('name="from"', html)

    def test_empty_database_returns_genuine_empty_state(self):
        app=create_app()
        app.testing=True
        with patch("routes.reports.get_connection", return_value=Connection([])):
            with app.test_client() as client:
                response=client.get("/reports")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Geen bestellingen gevonden.", response.get_data(as_text=True))

    def test_route_uses_one_read_only_query(self):
        connection=Connection(self.rows)
        app=create_app()
        app.testing=True
        with patch("routes.reports.get_connection",return_value=connection):
            with app.test_client() as client:
                response=client.get("/reports?from=2026-01-01")
        self.assertEqual(response.status_code,200)
        self.assertIn("SELECT",connection.cur.sql)
        self.assertNotIn("INSERT",connection.cur.sql.upper())
        self.assertNotIn("UPDATE",connection.cur.sql.upper())
