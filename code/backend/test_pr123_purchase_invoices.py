"""Purchase invoice payment registration required by AD25 and current process."""
from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, NotFoundError
from repositories.assessed_repository import AssessedRepository


class StubCursor:
    def __init__(self, invoice):
        self.invoice = invoice
        self.query = ""
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.query = query
        self.statements.append((query, params))

    def fetchone(self):
        return self.invoice


class StubDB:
    def __init__(self, invoice):
        self.cursor_instance = StubCursor(invoice)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class PurchaseInvoiceCaseTests(TestCase):
    def test_unpaid_supplier_invoice_is_marked_paid_once(self):
        db = StubDB({"inkoopfactuur_id": 12, "betaald_op": None})
        AssessedRepository(db).mark_purchase_invoice_paid(12, date(2026, 11, 1))
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertTrue(any("UPDATE Inkoopfactuur" in query
                            for query, _ in db.cursor_instance.statements))

    def test_unknown_or_already_paid_invoice_is_rejected(self):
        for value, error in ((None, NotFoundError),
                             ({"inkoopfactuur_id": 12,
                               "betaald_op": date(2026, 10, 1)}, ConflictError)):
            with self.subTest(value=value):
                db = StubDB(value)
                with self.assertRaises(error):
                    AssessedRepository(db).mark_purchase_invoice_paid(
                        12, date(2026, 11, 1)
                    )
                self.assertEqual(db.rollbacks, 1)
                self.assertEqual(db.commits, 0)

    def test_supplier_invoice_list_is_visible_on_invoice_screen(self):
        app = create_app()
        app.testing = True
        data = [{"inkoopfactuur_id": 12, "factuurdatum": date(2026, 10, 22),
                 "bedrag": Decimal("120.00"), "leverancier": "Fabrikant A"}]
        with app.test_client() as client, patch(
            "routes.administration.get_connection", return_value=object()
        ), patch("routes.administration.AssessedRepository") as repository:
            repository.return_value.outstanding_purchase_invoices.return_value = data
            response = client.get("/invoices")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Openstaande inkoopfacturen", response.data)
        self.assertIn(b"Fabrikant A", response.data)
        self.assertIn(b"Betaling registreren", response.data)
        self.assertIn(b"geen bankbetaling uit", response.data)

    def test_payment_route_requires_explicit_confirmation(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            unconfirmed = client.post("/purchase-invoices/12/paid", data={})
            self.assertEqual(unconfirmed.status_code, 400)
            with patch(
                "routes.administration.get_connection", return_value=object()
            ), patch("routes.administration.AssessedRepository") as repository:
                confirmed = client.post("/purchase-invoices/12/paid",
                                        data={"payment_confirmed": "yes"})
                self.assertEqual(confirmed.status_code, 302)
                repository.return_value.mark_purchase_invoice_paid.assert_called_once()
