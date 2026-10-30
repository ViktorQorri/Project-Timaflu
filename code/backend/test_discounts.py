"""Order discount calculation (SD01) without a live MySQL server; nothing is written."""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError, NotFoundError
from repositories.discount_repository import DiscountRepository
from services.discount_service import DiscountService

CUSTOMER = {"klant_id": 7, "bedrijfsnaam": "Apotheek De Brug"}
PRODUCTS = {
    1: {"product_id": 1, "artikelnummer": "TIM-1", "productnaam": "Medicine A",
        "prijs_per_grootverpakking": Decimal("100.00")},
    2: {"product_id": 2, "artikelnummer": "TIM-2", "productnaam": "Medicine B",
        "prijs_per_grootverpakking": Decimal("0.01")},
}


class FakeRepository:
    def __init__(self, previous_orders=3, revenue=Decimal("0")):
        self.previous_orders = previous_orders
        self.revenue = revenue
        self.purchase_years = []

    def list_customers(self):
        return [CUSTOMER]

    def list_products(self):
        return list(PRODUCTS.values())

    def find_customer(self, customer_id):
        return CUSTOMER if customer_id == CUSTOMER["klant_id"] else None

    def find_product(self, product_id):
        return PRODUCTS.get(product_id)

    def count_previous_orders(self, customer_id):
        return self.previous_orders

    def sum_purchases(self, customer_id, year):
        self.purchase_years.append((customer_id, year))
        return self.revenue


class Cursor:
    """Answers each query by a word in its SQL, like the tables in schema.sql."""

    def __init__(self, previous_orders, revenue):
        self.answers = {
            "COUNT(*)": {"aantal_bestellingen": previous_orders},
            "jaaromzet": {"jaaromzet": revenue},
            "WHERE klant_id": CUSTOMER,
            "WHERE product_id": PRODUCTS[1],
        }
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.statements.append((query, params))

    def fetchone(self):
        query = self.statements[-1][0]
        return next(row for word, row in self.answers.items() if word in query)

    def fetchall(self):
        return [CUSTOMER] if "FROM Klant" in self.statements[-1][0] else list(PRODUCTS.values())


class Connection:
    def __init__(self, previous_orders=3, revenue=Decimal("12000.00")):
        self.c = Cursor(previous_orders, revenue)
        self.commits = 0

    def cursor(self, dictionary=False):
        assert dictionary
        return self.c

    def commit(self):
        self.commits += 1


def calculate(repository, lines, order_date=date(2026, 10, 30)):
    return DiscountService(repository).calculate_total_amount("7", lines, order_date)


class OrderDiscountTests(TestCase):
    def test_no_order_discount_below_500(self):
        result = calculate(FakeRepository(), [("1", "4"), ("2", "9999")])
        self.assertEqual(result["subtotal"], Decimal("499.99"))
        self.assertEqual([d["kind"] for d in result["discounts"]], ["customer"])

    def test_order_discount_at_500(self):
        result = calculate(FakeRepository(), [("1", "5")])
        order_discount = result["discounts"][0]
        self.assertEqual(order_discount["kind"], "order")
        self.assertEqual(order_discount["amount"], Decimal("25.00"))
        self.assertEqual(order_discount["total_after"], Decimal("475.00"))

    def test_order_discount_above_500(self):
        self.assertEqual(calculate(FakeRepository(), [("1", "10")])["discounts"][0]["amount"], Decimal("50.00"))

    def test_customer_discount_tiers_by_annual_revenue(self):
        tiers = {"0": 5, "9999.99": 5, "10000": 10, "10000.00": 10, "19999.99": 10, "20000": 15, "250000": 15}
        for revenue, percentage in tiers.items():
            with self.subTest(revenue=revenue):
                self.assertEqual(DiscountService.determine_discount_percentage(Decimal(revenue)), percentage)

    def test_first_order_gets_one_time_discount_only(self):
        repository = FakeRepository(previous_orders=0, revenue=Decimal("50000"))
        result = calculate(repository, [("1", "10")])
        self.assertTrue(result["first_order"])
        self.assertEqual([d["kind"] for d in result["discounts"]], ["order", "one_time"])
        self.assertEqual(result["discounts"][1]["amount"], Decimal("95.00"))
        self.assertEqual(result["total_amount"], Decimal("855.00"))
        self.assertEqual(repository.purchase_years, [])

    def test_existing_customer_discount_over_amount_after_order_discount(self):
        repository = FakeRepository(previous_orders=2, revenue=Decimal("15000.00"))
        result = calculate(repository, [("1", "10")])
        self.assertFalse(result["first_order"])
        self.assertEqual(repository.purchase_years, [(7, 2025)])
        self.assertEqual(result["annual_revenue"], Decimal("15000.00"))
        customer_discount = result["discounts"][1]
        self.assertEqual((customer_discount["percentage"], customer_discount["base"]), (Decimal("10"), Decimal("950.00")))
        self.assertEqual(customer_discount["amount"], Decimal("95.00"))
        self.assertEqual(result["total_amount"], Decimal("855.00"))

    def test_rounds_to_cents_half_up_per_step(self):
        result = calculate(FakeRepository(revenue=Decimal("25000")), [("1", "5"), ("2", "10")])
        self.assertEqual(result["subtotal"], Decimal("500.10"))
        self.assertEqual(result["discounts"][0]["amount"], Decimal("25.01"))  # 25.005
        self.assertEqual(result["discounts"][1]["amount"], Decimal("71.26"))  # 15% of 475.09 = 71.2635
        self.assertEqual(result["total_amount"], Decimal("403.83"))

    def test_empty_rows_are_ignored(self):
        result = calculate(FakeRepository(), [("", ""), ("1", "1"), (None, None)])
        self.assertEqual(len(result["lines"]), 1)

    def test_invalid_input_rejected(self):
        cases = {
            "no lines": ("7", [("", "")]),
            "quantity zero": ("7", [("1", "0")]),
            "quantity text": ("7", [("1", "veel")]),
            "missing quantity": ("7", [("1", "")]),
            "duplicate product": ("7", [("1", "1"), ("1", "2")]),
            "no customer": ("", [("1", "1")]),
            "negative customer": ("-3", [("1", "1")]),
        }
        for name, (customer_id, lines) in cases.items():
            with self.subTest(name), self.assertRaises(DomainError):
                DiscountService(FakeRepository()).calculate_total_amount(customer_id, lines)
        for revenue in (Decimal("-0.01"), "geen bedrag", None):
            with self.subTest(revenue=revenue), self.assertRaises(DomainError):
                DiscountService.determine_discount_percentage(revenue)

    def test_unknown_customer_or_product_not_found(self):
        service = DiscountService(FakeRepository())
        with self.assertRaises(NotFoundError):
            service.calculate_total_amount("8", [("1", "1")])
        with self.assertRaises(NotFoundError):
            service.calculate_total_amount("7", [("99", "1")])

    def test_repository_queries_use_placeholders(self):
        connection = Connection(previous_orders=4, revenue=Decimal("1234.50"))
        repository = DiscountRepository(connection)
        self.assertEqual(repository.count_previous_orders(7), 4)
        self.assertEqual(connection.c.statements[-1][1], (7,))
        self.assertEqual(repository.sum_purchases(7, 2025), Decimal("1234.50"))
        query, params = connection.c.statements[-1]
        self.assertIn("JOIN Bestelregel", query)
        self.assertIn("YEAR(b.besteld_op) = %s", query)
        self.assertEqual(params, (7, 2025))
        self.assertEqual(repository.find_product(1), PRODUCTS[1])
        self.assertEqual(connection.commits, 0)

    def test_discount_page_shows_breakdown_and_errors(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection()):
                response = client.get("/orders/discount")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Korting berekenen", response.data)
                self.assertIn(b"Apotheek De Brug", response.data)
            with patch("routes.sales.get_connection", return_value=Connection()):
                response = client.get("/orders/discount?customer_id=7&product_id=1&quantity=10&product_id=&quantity=")
                self.assertEqual(response.status_code, 200)
                page = response.get_data(as_text=True)
                self.assertIn("Bestellingskorting (5% over € 1.000,00)", page)
                self.assertIn("Klantenkorting (10% over € 950,00)", page)
                self.assertIn("€ 855,00", page)
            with patch("routes.sales.get_connection", return_value=Connection()):
                response = client.get("/orders/discount?customer_id=7&product_id=1&quantity=0")
                self.assertEqual(response.status_code, 400)
                self.assertIn("Het aantal moet een positief geheel getal zijn.", response.get_data(as_text=True))
