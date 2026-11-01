"""Order discount calculation (SD01) without a live MySQL server; nothing is written.

The order screen that shows it is tested in test_orders.py."""

from datetime import date
from decimal import Decimal
from unittest import TestCase

from domain.errors import DomainError, NotFoundError
from repositories.discount_repository import DiscountRepository
from services.discount_service import DiscountService

CUSTOMER = {"klant_id": 7, "bedrijfsnaam": "Apotheek De Brug", "eenmalige_korting_toegezegd": False}
PRODUCTS = {
    1: {"product_id": 1, "artikelnummer": "TIM-1", "productnaam": "Medicine A",
        "prijs_per_grootverpakking": Decimal("100.00")},
    2: {"product_id": 2, "artikelnummer": "TIM-2", "productnaam": "Medicine B",
        "prijs_per_grootverpakking": Decimal("0.01")},
}


class FakeRepository:
    def __init__(self, previous_orders=3, revenue=Decimal("0"),
                 percentage=Decimal("5"), percentages=None, revenues=None):
        self.previous_orders = previous_orders
        self.revenue = revenue
        self.revenues = revenues
        self.percentages = {2026: percentage} if percentages is None else percentages
        self.purchase_years = []
        self.discount_years = []
        self.annual_saves = []

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

    def get_customer_discount_percentage(self, customer_id, year):
        self.discount_years.append((customer_id, year))
        return self.percentages.get(year)

    def list_customer_ids(self):
        return sorted(self.revenues) if self.revenues is not None else [CUSTOMER["klant_id"]]

    def save_annual_discounts(self, year, rates):
        self.annual_saves.append((year, rates))

    def sum_purchases(self, customer_id, year):
        self.purchase_years.append((customer_id, year))
        return self.revenues[customer_id] if self.revenues is not None else self.revenue


class Cursor:
    """Answers each query by a word in its SQL, like the tables in schema.sql."""

    def __init__(self, previous_orders, revenue, percentage=Decimal("10")):
        self.percentage = percentage
        self.answers = {
            "COUNT(*)": {"aantal_bestellingen": previous_orders},
            "jaaromzet": {"jaaromzet": revenue, "betaalde_facturen": 1, "facturen_met_bedrag": 1},
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
        if "FROM Klantkorting" in query:
            return None if self.percentage is None else {"percentage": self.percentage}
        if "AS jaaromzet" in query:
            return self.answers["jaaromzet"]
        return next(row for word, row in self.answers.items() if word in query)

    def fetchall(self):
        return [CUSTOMER] if "FROM Klant" in self.statements[-1][0] else list(PRODUCTS.values())


class Connection:
    def __init__(self, previous_orders=3, revenue=Decimal("12000.00"),
                 percentage=Decimal("10")):
        self.c = Cursor(previous_orders, revenue, percentage)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        assert dictionary
        return self.c

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def calculate(repository, lines, order_date=date(2026, 10, 30)):
    return DiscountService(repository).calculate_total_amount("7", lines, order_date)


class OrderDiscountTests(TestCase):
    def test_no_order_discount_below_500(self):
        result = calculate(FakeRepository(), [("1", "4"), ("2", "4999")])
        self.assertEqual(result["subtotal"], Decimal("449.99"))
        self.assertEqual(result["vat_amount"], Decimal("40.50"))
        self.assertEqual(result["gross_total"], Decimal("490.49"))
        self.assertEqual([d["kind"] for d in result["discounts"]], ["customer"])

    def test_order_discount_at_500(self):
        result = calculate(FakeRepository(), [("1", "5")])
        order_discount = result["discounts"][0]
        self.assertEqual(order_discount["kind"], "order")
        self.assertEqual(result["gross_total"], Decimal("545.00"))
        self.assertEqual(order_discount["amount"], Decimal("27.25"))
        self.assertEqual(order_discount["total_after"], Decimal("517.75"))

    def test_order_discount_above_500(self):
        self.assertEqual(calculate(FakeRepository(), [("1", "10")])["discounts"][0]["amount"], Decimal("54.50"))

    def test_customer_discount_tiers_by_annual_revenue(self):
        tiers = {"0": 5, "9999.99": 5, "10000": 10, "10000.00": 10, "19999.99": 10, "20000": 15, "250000": 15}
        for revenue, percentage in tiers.items():
            with self.subTest(revenue=revenue):
                self.assertEqual(DiscountService.determine_discount_percentage(Decimal(revenue)), percentage)

    def test_first_order_gets_one_time_and_customer_discount(self):
        repository = FakeRepository(previous_orders=0, revenue=Decimal("50000"), percentage=Decimal("15"))
        result = calculate(repository, [("1", "10")])
        self.assertTrue(result["first_order"])
        self.assertEqual([d["kind"] for d in result["discounts"]], ["order", "one_time", "customer"])
        self.assertEqual(result["discounts"][1]["amount"], Decimal("103.55"))
        self.assertEqual(result["discounts"][2]["base"], Decimal("931.95"))
        self.assertEqual(result["discounts"][2]["amount"], Decimal("139.79"))
        self.assertEqual(result["total_amount"], Decimal("792.16"))
        self.assertEqual(repository.purchase_years, [])
        self.assertEqual(repository.discount_years, [(7, 2026)])

    def test_first_order_always_gets_ten_percent_without_acquisition_promise(self):
        self.assertFalse(CUSTOMER["eenmalige_korting_toegezegd"])
        result = calculate(FakeRepository(previous_orders=0), [("1", "10")])
        self.assertTrue(result["first_order"])
        self.assertTrue(result["one_time_discount"])
        self.assertEqual([d["kind"] for d in result["discounts"]],
                         ["order", "one_time", "customer"])
        self.assertEqual(result["discounts"][1]["amount"], Decimal("103.55"))
        self.assertEqual(result["total_amount"], Decimal("885.35"))

    def test_new_customer_without_year_record_gets_and_keeps_base_rate(self):
        repository = FakeRepository(previous_orders=0, percentages={})
        result = calculate(repository, [("1", "10")])
        self.assertEqual(result["customer_discount_percentage"], Decimal("5"))
        self.assertEqual(result["total_amount"], Decimal("885.35"))

    def test_existing_customer_missing_year_record_is_rejected(self):
        with self.assertRaisesRegex(DomainError, "klantenkorting voor 2026"):
            calculate(FakeRepository(previous_orders=1, percentages={}), [("1", "1")])

    def test_only_stored_rate_is_used_even_when_revenue_differs(self):
        repository = FakeRepository(previous_orders=2, revenue=Decimal("2000000"),
                                    percentage=Decimal("5"))
        result = calculate(repository, [("1", "10")])
        self.assertEqual(result["total_amount"], Decimal("983.72"))
        self.assertEqual(repository.purchase_years, [])
        self.assertEqual(result["customer_discount_percentage"], Decimal("5"))

    def test_year_boundaries_use_rates_for_the_correct_calendar_year(self):
        repository = FakeRepository(previous_orders=2,
                                    percentages={2026: Decimal("5"), 2027: Decimal("15")})
        old = calculate(repository, [("1", "10")], date(2026, 12, 31))
        new = calculate(repository, [("1", "10")], date(2027, 1, 1))
        self.assertEqual(old["total_amount"], Decimal("983.72"))
        self.assertEqual(new["total_amount"], Decimal("880.17"))
        self.assertEqual(repository.discount_years, [(7, 2026), (7, 2027)])

    def test_year_end_stores_tiers_for_next_year_once(self):
        repository = FakeRepository(revenues={
            7: Decimal("9999.99"), 8: Decimal("10000.00"), 9: Decimal("20000.00")
        })
        result = DiscountService(repository).update_annual_discounts(date(2026, 12, 31))
        self.assertEqual(result, {"discount_year": 2027, "customers": 3})
        self.assertEqual(repository.annual_saves, [(2027, [
            (7, Decimal("5")), (8, Decimal("10")), (9, Decimal("15"))
        ])])
        self.assertEqual(repository.purchase_years, [(7, 2026), (8, 2026), (9, 2026)])

    def test_annual_process_refuses_any_day_other_than_december_31(self):
        repository = FakeRepository(revenues={7: Decimal("25000.00")})
        with self.assertRaisesRegex(DomainError, "31 december"):
            DiscountService(repository).update_annual_discounts(date(2026, 12, 30))
        self.assertEqual(repository.purchase_years, [])
        self.assertEqual(repository.annual_saves, [])

    def test_existing_customer_discount_over_amount_after_order_discount(self):
        repository = FakeRepository(previous_orders=2, revenue=Decimal("15000.00"), percentage=Decimal("10"))
        result = calculate(repository, [("1", "10")])
        self.assertFalse(result["first_order"])
        self.assertEqual(repository.purchase_years, [])
        self.assertEqual(result["discount_year"], 2026)
        self.assertEqual(result["customer_discount_percentage"], Decimal("10"))
        customer_discount = result["discounts"][1]
        self.assertEqual((customer_discount["percentage"], customer_discount["base"]), (Decimal("10"), Decimal("1035.50")))
        self.assertEqual(customer_discount["amount"], Decimal("103.55"))
        self.assertEqual(result["total_amount"], Decimal("931.95"))

    def test_rounds_to_cents_half_up_per_step(self):
        result = calculate(FakeRepository(revenue=Decimal("25000"), percentage=Decimal("15")),
                           [("1", "5"), ("2", "10")])
        self.assertEqual(result["subtotal"], Decimal("500.10"))
        self.assertEqual(result["vat_amount"], Decimal("45.01"))
        self.assertEqual(result["discounts"][0]["amount"], Decimal("27.26"))
        self.assertEqual(result["discounts"][1]["amount"], Decimal("77.68"))
        self.assertEqual(result["total_amount"], Decimal("440.17"))

    def test_complete_order_quote_matches_the_case_invoice_calculation(self):
        from domain.business import Invoice

        result = calculate(FakeRepository(previous_orders=0, percentage=Decimal("15")),
                           [("1", "10")])
        invoice = Invoice(7, "INV-TEST", date(2026, 10, 30)).createWeeklyInvoice(
            "Apotheek De Brug", "Teststraat",
            [{"quantity": 10, "unit_price": Decimal("100")}],
            annualRevenue=0, firstOrder=True,
            customerDiscountPercentage=Decimal("15"),
        )
        self.assertEqual(result["subtotal"], invoice["total_ex_vat"])
        self.assertEqual(result["vat_amount"], invoice["vat_9_percent"])
        self.assertEqual(result["gross_total"], invoice["total_incl_vat"])
        self.assertEqual(result["discounts"][0]["amount"], invoice["order_discount"])
        self.assertEqual(result["discounts"][1]["amount"], invoice["first_order_discount"])
        self.assertEqual(result["discounts"][2]["amount"], invoice["customer_discount"])
        self.assertEqual(result["total_amount"], invoice["total"])

    def test_empty_rows_are_ignored(self):
        result = calculate(FakeRepository(), [("", ""), ("1", "1"), (None, None)])
        self.assertEqual(len(result["lines"]), 1)

    def test_minimum_order_quantity_comes_from_product_catalogue(self):
        product = PRODUCTS[1]
        original = product.get("minimale_bestelhoeveelheid")
        try:
            product["minimale_bestelhoeveelheid"] = 3
            with self.assertRaisesRegex(DomainError, "Minimale bestelhoeveelheid"):
                calculate(FakeRepository(), [("1", "2")])
            self.assertEqual(calculate(FakeRepository(), [("1", "3")])["lines"][0]["quantity"], 3)
        finally:
            if original is None:
                product.pop("minimale_bestelhoeveelheid")
            else:
                product["minimale_bestelhoeveelheid"] = original

    def test_telephone_order_accepts_thirteen_distinct_lines_without_arbitrary_limit(self):
        from datetime import timedelta
        from repositories.telephone_order_repository import TelephoneOrderRepository

        requested = [
            {"product_id": index, "quantity": 1, "shortage": "skip"}
            for index in range(1, 14)
        ]
        customer, validated = TelephoneOrderRepository.validate(
            7, requested, date.today() + timedelta(days=1), "ochtend", False
        )
        self.assertEqual(customer, 7)
        self.assertEqual(len(validated), 13)

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
        self.assertEqual(repository.get_customer_discount_percentage(7, 2026), Decimal("10"))
        self.assertIn("FROM Klantkorting", connection.c.statements[-1][0])
        self.assertEqual(connection.c.statements[-1][1], (7, 2026))
        self.assertEqual(repository.sum_purchases(7, 2025), Decimal("1234.50"))
        query, params = connection.c.statements[-1]
        self.assertIn("SUM(f.totaal_bedrag)", query)
        self.assertIn("YEAR(f.betaald_op) = %s", query)
        self.assertEqual(params, (7, 2025))
        self.assertEqual(repository.find_product(1), PRODUCTS[1])
        self.assertIn("in_assortiment = TRUE", connection.c.statements[-1][0])
        self.assertEqual(connection.commits, 0)

    def test_annual_repository_writes_new_rate_and_is_idempotent(self):
        connection = Connection(percentage=None)
        repository = DiscountRepository(connection)
        repository.save_annual_discounts(2027, [(7, Decimal("5"))])
        self.assertEqual(connection.commits, 1)
        inserts = [(query, params) for query, params in connection.c.statements
                   if "INSERT INTO Klantkorting" in query]
        self.assertEqual(inserts[0][1], (7, 2027, Decimal("5")))

        existing = Connection(percentage=Decimal("5"))
        DiscountRepository(existing).save_annual_discounts(2027, [(7, Decimal("5"))])
        self.assertEqual(existing.commits, 1)
        self.assertFalse(any("INSERT INTO Klantkorting" in q for q, _ in existing.c.statements))

    def test_annual_repository_refuses_changing_a_fixed_rate(self):
        connection = Connection(percentage=Decimal("10"))
        with self.assertRaisesRegex(DomainError, "al anders vastgesteld"):
            DiscountRepository(connection).save_annual_discounts(2027, [(7, Decimal("15"))])
        self.assertEqual((connection.commits, connection.rollbacks), (0, 1))
