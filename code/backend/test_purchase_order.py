"""Purchasing-order tests; no real supplier order is sent or database modified."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService


class Cursor:
    def __init__(self, found=True):
        self.commands = []
        self.lastrowid = 42
        self.found = found

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, values):
        self.commands.append((query, values))

    def fetchone(self):
        return (1,) if self.found else None


class Connection:
    def __init__(self, found=True):
        self.cur = Cursor(found)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class PurchasingOrderTests(TestCase):
    def test_transaction_and_supplier_product_check(self):
        db = Connection()
        result = PurchaseOrderService(PurchaseOrderRepository(db)).record_order("3", "9", "5")
        self.assertEqual(result, 42)
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertEqual(len(db.cur.commands), 3)
        self.assertEqual(db.cur.commands[0][1], (3, 9))
        self.assertIn("p.intern_bestelbaar = TRUE", db.cur.commands[0][0])
        self.assertEqual(db.cur.commands[2][1], (42, 9, 5))

    def test_reject_invalid_quantity_without_writes(self):
        db = Connection()
        with self.assertRaises(DomainError):
            PurchaseOrderService(PurchaseOrderRepository(db)).record_order(3, 9, 0)
        self.assertFalse(db.cur.commands)

    def test_supplier_must_offer_product(self):
        db = Connection(found=False)
        with self.assertRaises(DomainError):
            PurchaseOrderService(PurchaseOrderRepository(db)).record_order(3, 9, 5)
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.rollbacks, 1)

    def test_form_records_only_explicit_submit(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.purchasing.get_connection", return_value=Connection()):
                refused = client.post("/purchase-orders", data={
                    "supplier_id": "3", "product_id": "9", "quantity": "5"
                })
                self.assertEqual(refused.status_code, 400)
                response = client.post("/purchase-orders", data={
                    "supplier_id": "3", "product_id": "9", "quantity": "5",
                    "supplier_contact_confirmed": "yes"
                })
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.headers["Location"].endswith("/suppliers"))
