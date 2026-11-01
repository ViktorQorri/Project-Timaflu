"""Casus AD28: annual customer discounts are fixed on December 31."""
from datetime import date
from decimal import Decimal
from unittest import TestCase

from domain.business import Invoice
from domain.errors import ConflictError, DomainError
from repositories.assessed_repository import AssessedRepository
from services.discount_service import DiscountService
from test_discounts import FakeRepository


class AnnualCursor:
    def __init__(self, db):
        self.db = db
        self.query = ""
        self.params = None
        self.lastrowid = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.query = " ".join(query.split())
        self.params = params
        self.db.executed.append((self.query, params))

    def fetchall(self):
        if "SELECT klant_id FROM Klant" in self.query:
            return [{"klant_id": 1}, {"klant_id": 2}]
        raise AssertionError(self.query)

    def fetchone(self):
        if "COUNT(*) AS aantal FROM Klantkorting" in self.query:
            return {"aantal": self.db.existing}
        if "COUNT(*) AS paid_count" in self.query:
            if self.params[0] == 1:
                return {"paid_count": 1, "known_count": 1, "jaaromzet": Decimal("9999.99")}
            return {"paid_count": 1, "known_count": self.db.second_known,
                    "jaaromzet": Decimal("20000.00")}
        raise AssertionError(self.query)


class AnnualDB:
    def __init__(self, existing=0, second_known=1):
        self.existing = existing
        self.second_known = second_known
        self.executed = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return AnnualCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class AnnualDiscountTests(TestCase):
    def test_december_31_saves_next_year_discount_for_all_customers(self):
        database = AnnualDB()
        count = AssessedRepository(database).determine_annual_customer_discounts(
            date(2026, 12, 31)
        )
        self.assertEqual(count, 2)
        inserts = [params for sql, params in database.executed
                   if sql.startswith("INSERT INTO Klantkorting")]
        self.assertEqual(inserts, [
            (1, 2027, Decimal("5")),
            (2, 2027, Decimal("15")),
        ])
        self.assertEqual(database.commits, 1)

    def test_discounts_cannot_be_reissued_or_guessed(self):
        for database, error in ((AnnualDB(existing=1), ConflictError),
                                (AnnualDB(second_known=0), DomainError)):
            with self.subTest(database=database), self.assertRaises(error):
                AssessedRepository(database).determine_annual_customer_discounts(
                    date(2026, 12, 31)
                )
            self.assertEqual(database.commits, 0)
            self.assertEqual(database.rollbacks, 1)

    def test_other_dates_cannot_recalculate_discount(self):
        database = AnnualDB()
        with self.assertRaisesRegex(DomainError, "31 december"):
            AssessedRepository(database).determine_annual_customer_discounts(
                date(2026, 11, 1)
            )
        self.assertEqual(database.executed, [])

    def test_saved_annual_rate_overrides_dynamic_recalculation(self):
        class SavedRepository(FakeRepository):
            def get_customer_discount_percentage(self, customer_id, year):
                self.saved_year = year
                return Decimal("15")
        repo = SavedRepository(revenue=Decimal("0"))
        calculation = DiscountService(repo).calculate_total_amount(
            7, [(1, 1)], date(2027, 2, 1)
        )
        self.assertEqual(repo.saved_year, 2027)
        self.assertEqual(calculation["discounts"][-1]["percentage"], Decimal("15"))

    def test_invoice_uses_order_year_saved_rate(self):
        invoice = Invoice(7, "1", date(2027, 2, 1)).createWeeklyInvoice(
            "Apotheek", "Adres", [
                {"bestelling_id": 4, "quantity": 1, "unit_price": Decimal("100"),
                 "eenmalige_korting_toegepast": False,
                 "annual_discount_percentage": Decimal("15")}
            ],
            Decimal("0"), False
        )
        self.assertEqual(invoice["customer_discount"], Decimal("16.35"))
