"""Tests for the sales reports, without requiring a live MySQL server."""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from repositories.sales_report_repository import SalesReportRepository
from services.sales_report_service import SalesReportService, format_euro


class FakeCursor:
    """Answers each report query with its own rows and records what was executed."""

    def __init__(self, customers, periods, products):
        self.customers = customers
        self.periods = periods
        self.products = products
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.executed.append((query, params))

    def fetchall(self):
        query = self.executed[-1][0]
        if "DATE_FORMAT" in query:
            return self.periods
        if "LIMIT" in query:
            return self.products
        return self.customers


class FakeConnection:
    def __init__(self, customers=(), periods=(), products=()):
        self.cursor_instance = FakeCursor(list(customers), list(periods), list(products))

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cursor_instance


class FakeRepository:
    def __init__(self, customers=(), periods=(), products=()):
        self.customers = list(customers)
        self.periods = list(periods)
        self.products = list(products)
        self.calls = []

    def revenue_per_customer(self, start, end):
        self.calls.append(("customers", start, end))
        return self.customers

    def revenue_per_period(self, date_format, start, end):
        self.calls.append(("periods", date_format, start, end))
        return self.periods

    def best_selling_products(self, start, end, limit):
        self.calls.append(("products", start, end, limit))
        return self.products


CUSTOMERS = [
    {"klant_id": 1, "bedrijfsnaam": "Apotheek Noord", "aantal_bestellingen": 2, "omzet": Decimal("750.00")},
    {"klant_id": 2, "bedrijfsnaam": "Apotheek Zuid", "aantal_bestellingen": 1, "omzet": Decimal("250.00")},
]
PERIODS = [
    {"periode": "2026-01", "aantal_bestellingen": 2, "omzet": Decimal("800.00")},
    {"periode": "2026-03", "aantal_bestellingen": 1, "omzet": Decimal("200.00")},
]
PRODUCTS = [
    {"product_id": 7, "artikelnummer": "TIM-7", "productnaam": "Paracetamol", "aantal_verkocht": Decimal("40"), "omzet": Decimal("600.00")},
    {"product_id": 3, "artikelnummer": "TIM-3", "productnaam": "Ibuprofen", "aantal_verkocht": Decimal("25"), "omzet": Decimal("400.00")},
]


class SalesReportRepositoryTests(TestCase):
    def test_revenue_per_customer_sums_order_lines_in_period(self):
        connection = FakeConnection(customers=CUSTOMERS)
        rows = SalesReportRepository(connection).revenue_per_customer(date(2026, 1, 1), date(2027, 1, 1))
        query, params = connection.cursor_instance.executed[0]
        self.assertEqual(rows, CUSTOMERS)
        self.assertIn("SUM(r.aantal * r.prijs_per_eenheid) AS omzet", query)
        self.assertIn("GROUP BY k.klant_id, k.bedrijfsnaam", query)
        self.assertIn("b.besteld_op >= %s AND b.besteld_op < %s", query)
        self.assertEqual(params, (date(2026, 1, 1), date(2027, 1, 1)))

    def test_revenue_per_period_groups_by_date_format(self):
        connection = FakeConnection(periods=PERIODS)
        rows = SalesReportRepository(connection).revenue_per_period("%Y-%m", date(2026, 1, 1), date(2027, 1, 1))
        query, params = connection.cursor_instance.executed[0]
        self.assertEqual(rows, PERIODS)
        self.assertIn("DATE_FORMAT(b.besteld_op, %s) AS periode", query)
        self.assertIn("GROUP BY periode", query)
        self.assertEqual(params, ("%Y-%m", date(2026, 1, 1), date(2027, 1, 1)))

    def test_best_selling_products_orders_by_quantity_with_limit(self):
        connection = FakeConnection(products=PRODUCTS)
        rows = SalesReportRepository(connection).best_selling_products(date(2026, 1, 1), date(2027, 1, 1), 10)
        query, params = connection.cursor_instance.executed[0]
        self.assertEqual(rows, PRODUCTS)
        self.assertIn("ORDER BY aantal_verkocht DESC", query)
        self.assertIn("LIMIT %s", query)
        self.assertEqual(params, (date(2026, 1, 1), date(2027, 1, 1), 10))


class SalesReportServiceTests(TestCase):
    def test_defaults_to_current_year_until_today_per_month(self):
        repository = FakeRepository()
        report = SalesReportService(repository).report(today=date(2026, 10, 30))
        self.assertEqual(report["start"], date(2026, 1, 1))
        self.assertEqual(report["end"], date(2026, 10, 30))
        self.assertEqual(report["grouping"], "month")
        # The last day is included by passing the next day as the excluded end.
        self.assertEqual(repository.calls[0], ("customers", date(2026, 1, 1), date(2026, 10, 31)))
        self.assertEqual(repository.calls[1], ("periods", "%Y-%m", date(2026, 1, 1), date(2026, 10, 31)))
        self.assertEqual(repository.calls[2], ("products", date(2026, 1, 1), date(2026, 10, 31), 10))

    def test_revenue_per_customer_totals_and_share(self):
        repository = FakeRepository(customers=CUSTOMERS, periods=PERIODS, products=PRODUCTS)
        report = SalesReportService(repository).report("2026-01-01", "2026-03-31", "month")
        self.assertEqual(report["total_revenue"], Decimal("1000.00"))
        self.assertEqual(report["total_orders"], 3)
        self.assertEqual(report["customer_count"], 2)
        self.assertEqual(report["average_order_value"], Decimal("333.33"))
        self.assertEqual(report["customers"][0]["aandeel"], Decimal("75.0"))
        self.assertEqual(report["customers"][1]["aandeel"], Decimal("25.0"))

    def test_revenue_per_period_includes_periods_without_sales(self):
        repository = FakeRepository(customers=CUSTOMERS, periods=PERIODS)
        periods = SalesReportService(repository).report("2026-01-15", "2026-03-10", "month")["periods"]
        self.assertEqual([period["periode"] for period in periods], ["2026-01", "2026-02", "2026-03"])
        self.assertEqual([period["label"] for period in periods], ["januari 2026", "februari 2026", "maart 2026"])
        self.assertEqual(periods[1]["omzet"], Decimal("0.00"))
        self.assertEqual(periods[1]["aantal_bestellingen"], 0)
        self.assertEqual(periods[0]["breedte"], Decimal("100.0"))
        self.assertEqual(periods[2]["breedte"], Decimal("25.0"))

    def test_week_and_day_keys_match_mysql_date_format(self):
        repository = FakeRepository(periods=[{"periode": "2026-W01", "aantal_bestellingen": 1, "omzet": Decimal("10")}])
        periods = SalesReportService(repository).report("2025-12-29", "2026-01-11", "week")["periods"]
        self.assertEqual(repository.calls[1][1], "%x-W%v")
        self.assertEqual([period["periode"] for period in periods], ["2026-W01", "2026-W02"])
        self.assertEqual(periods[0]["label"], "Week 1, 2026")
        self.assertEqual(periods[0]["omzet"], Decimal("10.00"))

        days = SalesReportService(FakeRepository()).report("2026-02-27", "2026-03-01", "day")["periods"]
        self.assertEqual([day["periode"] for day in days], ["2026-02-27", "2026-02-28", "2026-03-01"])
        self.assertEqual(days[0]["label"], "27-02-2026")

    def test_best_selling_medicines_are_converted_to_whole_numbers(self):
        repository = FakeRepository(customers=CUSTOMERS, products=PRODUCTS)
        products = SalesReportService(repository).report("2026-01-01", "2026-12-31", "year")["products"]
        self.assertEqual([product["productnaam"] for product in products], ["Paracetamol", "Ibuprofen"])
        self.assertEqual(products[0]["aantal_verkocht"], 40)
        self.assertIsInstance(products[0]["aantal_verkocht"], int)
        self.assertEqual(products[0]["omzet"], Decimal("600.00"))

    def test_empty_period_gives_zero_totals(self):
        report = SalesReportService(FakeRepository()).report("2026-05-01", "2026-05-31", "month")
        self.assertEqual(report["total_revenue"], Decimal("0"))
        self.assertEqual(report["total_orders"], 0)
        self.assertEqual(report["average_order_value"], Decimal("0.00"))
        self.assertEqual(report["customers"], [])
        self.assertEqual(report["products"], [])
        self.assertEqual(report["periods"][0]["omzet"], Decimal("0.00"))
        self.assertEqual(report["periods"][0]["breedte"], Decimal("0.0"))

    def test_invalid_filters_are_rejected_before_querying(self):
        for start, end, grouping in [
            ("2026-13-01", "2026-12-31", "month"),
            ("2026-01-01", "not a date", "month"),
            ("2026-06-01", "2026-05-31", "month"),
            ("2026-01-01", "2026-12-31", "quarter"),
        ]:
            repository = FakeRepository()
            with self.subTest(start=start, end=end, grouping=grouping):
                with self.assertRaises(DomainError):
                    SalesReportService(repository).report(start, end, grouping)
                self.assertEqual(repository.calls, [])

    def test_format_euro_uses_dutch_notation(self):
        self.assertEqual(format_euro(Decimal("1234.5")), "€ 1.234,50")
        self.assertEqual(format_euro(Decimal("0")), "€ 0,00")
        self.assertEqual(format_euro(None), "€ 0,00")


class SalesReportPageTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True

    def test_reports_page_links_to_sales_report(self):
        with self.app.test_client() as client:
            response = client.get("/reports")
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"/reports/sales", response.data)

    def test_sales_report_shows_all_three_reports(self):
        connection = FakeConnection(CUSTOMERS, PERIODS, PRODUCTS)
        with self.app.test_client() as client:
            with patch("routes.reports.get_connection", return_value=connection):
                response = client.get("/reports/sales?start=2026-01-01&end=2026-03-31&grouping=month")
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn("Omzet per klant", page)
        self.assertIn("Omzet per periode", page)
        self.assertIn("Best verkochte medicijnen", page)
        self.assertIn("Apotheek Noord", page)
        self.assertIn("februari 2026", page)
        self.assertIn("Paracetamol", page)
        self.assertIn("€ 1.000,00", page)
        self.assertIn("75,0%", page)
        self.assertEqual(len(connection.cursor_instance.executed), 3)

    def test_sales_report_empty_state(self):
        with self.app.test_client() as client:
            with patch("routes.reports.get_connection", return_value=FakeConnection()):
                response = client.get("/reports/sales?start=2026-05-01&end=2026-05-31")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Geen verkopen in deze periode", response.get_data(as_text=True))

    def test_invalid_period_keeps_filter_form_with_message(self):
        connection = FakeConnection()
        with self.app.test_client() as client:
            with patch("routes.reports.get_connection", return_value=connection):
                response = client.get("/reports/sales?start=2026-06-01&end=2026-05-31")
        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 400)
        self.assertIn("De begindatum moet op of vóór de einddatum liggen.", page)
        self.assertIn('value="2026-06-01"', page)
        self.assertEqual(connection.cursor_instance.executed, [])
