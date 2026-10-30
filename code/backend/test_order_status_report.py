"""Tests for the order status report, without requiring a live MySQL server."""

from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from repositories.order_status_report_repository import OrderStatusReportRepository
from services.order_status_report_service import OrderStatusReportService


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        self.sql, self.params = sql, params

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.cur = Cursor(rows)

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


class Repo:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def list_orders(self, date_from, date_to):
        self.calls.append((date_from, date_to))
        return self.rows


def order(order_id, status, customer="Apotheek De Linde"):
    return {
        "bestelling_id": order_id,
        "bedrijfsnaam": customer,
        "besteld_op": datetime(2026, 10, 12, 9, 30),
        "gewenste_leverdatum": date(2026, 10, 14),
        "dagdeel": "ochtend",
        "spoed": 0,
        "status_naam": status,
        "aantal_regels": 2,
    }


class OrderStatusReportTests(TestCase):
    def setUp(self):
        self.rows = [
            order(1, "wordt verzameld"),
            order(2, "verstuurd"),
            order(3, None),
            order(4, "backorder", "Ziekenhuis Oost"),
            order(5, "afgeleverd", "Huisartsenpost Noord"),
        ]

    def groups(self, report):
        return {group["key"]: group["orders"] for group in report["groups"]}

    def test_repository_reads_orders_with_customer_and_status(self):
        connection = Connection(self.rows)
        result = OrderStatusReportRepository(connection).list_orders(date(2026, 10, 1), None)
        self.assertEqual(result, self.rows)
        self.assertIn("JOIN Klant", connection.cur.sql)
        self.assertIn("LEFT JOIN Bestelregel", connection.cur.sql)
        self.assertIn("b.status_naam", connection.cur.sql)
        self.assertEqual(connection.cur.params, (date(2026, 10, 1), date(2026, 10, 1), None, None))

    def test_open_orders_include_every_unfinished_status(self):
        open_orders = self.groups(OrderStatusReportService(Repo(self.rows)).report("", ""))["open"]
        self.assertEqual([row["bestelling_id"] for row in open_orders], [1, 2, 3])

    def test_backorders_and_delivered_orders_are_separate(self):
        report = OrderStatusReportService(Repo(self.rows)).report("", "")
        groups = self.groups(report)
        self.assertEqual([row["bestelling_id"] for row in groups["backorder"]], [4])
        self.assertEqual([row["bestelling_id"] for row in groups["delivered"]], [5])
        self.assertEqual(report["total"], 5)

    def test_period_is_parsed_and_passed_to_repository(self):
        repo = Repo([])
        report = OrderStatusReportService(repo).report(" 2026-10-01 ", "2026-10-31")
        self.assertEqual(repo.calls, [(date(2026, 10, 1), date(2026, 10, 31))])
        self.assertEqual(report["date_from"], date(2026, 10, 1))
        self.assertEqual(report["total"], 0)

    def test_invalid_date_rejected_before_query(self):
        repo = Repo(self.rows)
        with self.assertRaises(DomainError):
            OrderStatusReportService(repo).report("31-10-2026", "")
        self.assertEqual(repo.calls, [])

    def test_start_after_end_rejected_before_query(self):
        repo = Repo(self.rows)
        with self.assertRaises(DomainError):
            OrderStatusReportService(repo).report("2026-11-01", "2026-10-01")
        self.assertEqual(repo.calls, [])

    def test_reports_page_renders_all_groups_and_empty_states(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.reports.get_connection", return_value=Connection(self.rows)):
                response = client.get("/reports")
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn("Openstaande orders", html)
                self.assertIn("Backorders", html)
                self.assertIn("Afgeleverde orders", html)
                self.assertIn("Ziekenhuis Oost", html)
                self.assertIn("Huisartsenpost Noord", html)
                self.assertIn("Wordt verzameld", html)
                self.assertIn("Nog geen status", html)
            with patch("routes.reports.get_connection", return_value=Connection([])):
                response = client.get("/reports?from=2026-10-01&to=2026-10-31")
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn("Geen backorders in deze periode", html)
                self.assertIn("01-10-2026", html)

    def test_reports_page_rejects_invalid_period(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.reports.get_connection", return_value=Connection(self.rows)):
                response = client.get("/reports?from=2026-11-01&to=2026-10-01")
                self.assertEqual(response.status_code, 400)
                self.assertIn("begindatum", response.get_data(as_text=True))
