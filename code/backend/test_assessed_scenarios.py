import unittest
from datetime import date
from services.assessed_scenarios import calculate_discount, cheapest_suppliers, outstanding_invoices, second_delivery_attempt, follow_up_prospects


class TestScenarios(unittest.TestCase):
    def test_discount(self):
        self.assertEqual(str(calculate_discount(500, 20000, True)["total"]), "363.37")

    def test_suppliers(self):
        offers = [{"product": "A", "price": 20, "supplier": "B"}, {"product": "A", "price": 10, "supplier": "A"}]
        self.assertEqual(cheapest_suppliers("A", offers)[0]["supplier"], "A")

    def test_unpaid(self):
        invoices = [{"customer_id": 1, "date": date(2026, 10, 1), "paid": False}]
        self.assertEqual(outstanding_invoices(1, invoices, date(2026, 10, 30))[0]["action"], "contact_payment_plan")

    def test_absent(self):
        rows = [{"order_id": 1, "date": date(2026, 10, 30)}]
        self.assertEqual(second_delivery_attempt(rows, date(2026, 10, 30), 1)[0]["second_attempt"], "scheduled")

    def test_prospect(self):
        visits = [{"prospect_id": 1, "date": date(2026, 9, 30)}]
        self.assertEqual(len(follow_up_prospects(visits, set(), date(2026, 10, 30))), 1)
