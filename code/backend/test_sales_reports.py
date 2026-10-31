"""Tests for sales reports based on saved invoice snapshots."""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from repositories.sales_report_repository import SalesReportRepository
from services.sales_report_service import SalesReportService, format_euro


class Cursor:
    def __init__(self):
        self.query = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.query, self.params = query, params

    def fetchall(self):
        return []


class Connection:
    def __init__(self):
        self.cur = Cursor()

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


class SalesReportTests(TestCase):
    def setUp(self):
        class Repository:
            def revenue_per_customer(self, start, end):
                return [
                    {
                        "klant_id": 1,
                        "bedrijfsnaam": "Apotheek A",
                        "aantal_facturen": 2,
                        "bekende_facturen": 2,
                        "onbekende_facturen": 0,
                        "bekend_factuurbedrag": Decimal("100.00"),
                    },
                    {
                        "klant_id": 2,
                        "bedrijfsnaam": "Apotheek B",
                        "aantal_facturen": 1,
                        "bekende_facturen": 0,
                        "onbekende_facturen": 1,
                        "bekend_factuurbedrag": None,
                    },
                ]

            def revenue_per_period(self, date_format, start, end):
                return [{
                    "periode": "2026-10",
                    "aantal_facturen": 3,
                    "bekende_facturen": 2,
                    "onbekende_facturen": 1,
                    "bekend_factuurbedrag": Decimal("100.00"),
                }]

            def best_selling_products(self, start, end, limit):
                return [{
                    "product_id": 3,
                    "artikelnummer": "MED-3",
                    "productnaam": "Medicijn A",
                    "aantal_verkocht": 12,
                }]

        self.repository = Repository()
        self.service = SalesReportService(self.repository)

    def test_incomplete_snapshots_never_become_zero_revenue(self):
        report = self.service.report(
            "2026-10-01", "2026-10-31", "month", today=date(2026, 10, 31)
        )
        self.assertIsNone(report["total_revenue"])
        self.assertEqual(report["known_invoice_total"], Decimal("100.00"))
        self.assertEqual(report["unknown_invoice_count"], 1)
        self.assertEqual(report["customers"][0]["omzet"], Decimal("100.00"))
        self.assertIsNone(report["customers"][1]["omzet"])
        self.assertIsNone(report["customers"][1]["bekend_factuurbedrag"])
        self.assertIsNone(report["periods"][0]["omzet"])
        self.assertEqual(report["products"][0]["aantal_verkocht"], 12)

    def test_complete_revenue_and_zero_periods(self):
        class CompleteRepository:
            def revenue_per_customer(self, start, end):
                return [{
                    "klant_id": 1,
                    "bedrijfsnaam": "Apotheek A",
                    "aantal_facturen": 1,
                    "bekende_facturen": 1,
                    "onbekende_facturen": 0,
                    "bekend_factuurbedrag": Decimal("109.00"),
                }]

            def revenue_per_period(self, date_format, start, end):
                return [{
                    "periode": "2026-10",
                    "aantal_facturen": 1,
                    "bekende_facturen": 1,
                    "onbekende_facturen": 0,
                    "bekend_factuurbedrag": Decimal("109.00"),
                }]

            def best_selling_products(self, start, end, limit):
                return []

        report = SalesReportService(CompleteRepository()).report(
            "2026-10-01", "2026-10-31", today=date(2026, 10, 31)
        )
        self.assertEqual(report["total_revenue"], Decimal("109.00"))
        self.assertEqual(report["average_invoice_value"], Decimal("109.00"))
        self.assertEqual(report["customers"][0]["aandeel"], Decimal("100.0"))

    def test_period_and_grouping_validation(self):
        with self.assertRaises(DomainError):
            self.service.report("2026-11-01", "2026-10-31", today=date(2026, 10, 31))
        with self.assertRaises(DomainError):
            self.service.report("", "", "decade", today=date(2026, 10, 31))
        with self.assertRaises(DomainError):
            self.service.report("not-a-date", "", today=date(2026, 10, 31))

    def test_repository_queries_invoice_snapshots_and_delivered_lines(self):
        connection = Connection()
        repository = SalesReportRepository(connection)
        repository.revenue_per_customer(date(2026, 1, 1), date(2027, 1, 1))
        self.assertIn("FROM Factuur AS f", connection.cur.query)
        self.assertIn("COUNT(f.totaal_bedrag)", connection.cur.query)
        self.assertEqual(connection.cur.params, (date(2026, 1, 1), date(2027, 1, 1)))

        repository.best_selling_products(date(2026, 1, 1), date(2027, 1, 1), 10)
        self.assertIn("JOIN Leveringregel AS lr", connection.cur.query)
        self.assertIn("SUM(lr.aantal_geleverd)", connection.cur.query)
        self.assertEqual(
            connection.cur.params,
            (date(2026, 1, 1), date(2027, 1, 1), 10),
        )

    def test_template_marks_missing_snapshots_as_unknown(self):
        app = create_app()
        app.config["TESTING"] = True
        with patch(
            "routes.reports.SalesReportRepository",
            return_value=self.repository,
        ), patch("routes.reports.get_connection", return_value=object()):
            with app.test_client() as client:
                response = client.get(
                    "/reports/sales?start=2026-10-01&end=2026-10-31"
                )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"historische snapshots", response.data)
        self.assertIn(b"Onbekend", response.data)
        self.assertIn(b"Medicijn A", response.data)

    def test_euro_format_does_not_hide_unknown_amounts(self):
        self.assertEqual(format_euro(None), "Onbekend")
        self.assertEqual(format_euro(Decimal("109.00")), "€ 109,00")
