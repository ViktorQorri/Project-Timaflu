"""Tests for management order-status reporting."""

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
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.query, self.params = query, params

    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.cur = Cursor(rows)

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


class OrderStatusReportTests(TestCase):
    def setUp(self):
        self.rows = [
            {"bestelling_id": 1, "status_naam": "nieuw"},
            {"bestelling_id": 2, "status_naam": "backorder"},
            {"bestelling_id": 3, "status_naam": "afgeleverd"},
            {"bestelling_id": 4, "status_naam": None},
        ]

    def test_service_groups_open_backorder_and_delivered_orders(self):
        class Repository:
            def list_orders(self, date_from, date_to):
                return rows

        rows = self.rows
        report = OrderStatusReportService(Repository()).report("", "")
        self.assertEqual(report["total"], 4)
        self.assertEqual(
            [len(group["orders"]) for group in report["groups"]],
            [2, 1, 1],
        )
        self.assertEqual(report["groups"][0]["orders"][1]["status_naam"], None)

    def test_dates_are_validated_and_endpoints_inclusive(self):
        class Repository:
            def list_orders(self, date_from, date_to):
                self.period = (date_from, date_to)
                return []

        repository = Repository()
        report = OrderStatusReportService(repository).report("2026-10-01", "2026-10-31")
        self.assertEqual(report["date_from"], date(2026, 10, 1))
        self.assertEqual(report["date_to"], date(2026, 10, 31))
        with self.assertRaises(DomainError):
            OrderStatusReportService(repository).report("2026-11-01", "2026-10-31")
        with self.assertRaises(DomainError):
            OrderStatusReportService(repository).report("not-a-date", "")

    def test_repository_uses_optional_date_bounds(self):
        connection = Connection(self.rows)
        OrderStatusReportRepository(connection).list_orders(
            date(2026, 10, 1), date(2026, 10, 31)
        )
        self.assertIn("LEFT JOIN Bestelregel", connection.cur.query)
        self.assertIn("INTERVAL 1 DAY", connection.cur.query)
        self.assertEqual(
            connection.cur.params,
            (date(2026, 10, 1), date(2026, 10, 1), date(2026, 10, 31), date(2026, 10, 31)),
        )

    def test_report_page_renders_each_status_group(self):
        rows = [
            {
                "bestelling_id": 1,
                "bedrijfsnaam": "Apotheek A",
                "besteld_op": datetime(2026, 10, 30, 10, 0),
                "gewenste_leverdatum": date(2026, 10, 31),
                "dagdeel": "ochtend",
                "spoed": False,
                "status_naam": "nieuw",
                "aantal_regels": 2,
            },
            {
                "bestelling_id": 2,
                "bedrijfsnaam": "Apotheek B",
                "besteld_op": datetime(2026, 10, 29, 10, 0),
                "gewenste_leverdatum": date(2026, 10, 31),
                "dagdeel": "middag",
                "spoed": False,
                "status_naam": "backorder",
                "aantal_regels": 1,
            },
            {
                "bestelling_id": 3,
                "bedrijfsnaam": "Apotheek C",
                "besteld_op": datetime(2026, 10, 28, 10, 0),
                "gewenste_leverdatum": date(2026, 10, 29),
                "dagdeel": "ochtend",
                "spoed": True,
                "status_naam": "afgeleverd",
                "aantal_regels": 3,
            },
        ]
        app = create_app()
        app.config["TESTING"] = True
        with patch(
            "routes.reports.get_connection",
            return_value=Connection(rows),
        ):
            with app.test_client() as client:
                response = client.get("/reports")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Openstaande orders", response.data)
        self.assertIn(b"Backorders", response.data)
        self.assertIn(b"Afgeleverde orders", response.data)
        self.assertIn(b"Apotheek C", response.data)
