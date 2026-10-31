"""Case regression tests for overdue invoices and consistent SQL examples."""
from datetime import date
from pathlib import Path
from unittest import TestCase

from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


class FakeCursor:
    def __init__(self, paid=False):
        self.paid = paid
        self.executed = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=()):
        self.executed.append((" ".join(sql.split()), params))

    def fetchall(self):
        return []

    def fetchone(self):
        return {
            "factuur_id": 12,
            "klant_id": 3,
            "factuurdatum": date(2026, 10, 1),
            "betaald_op": date(2026, 10, 10) if self.paid else None,
        }


class FakeDB:
    def __init__(self, paid=False):
        self.c = FakeCursor(paid=paid)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return self.c

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class OpenInvoiceCaseTests(TestCase):
    def test_unpaid_invoice_lookup_does_not_include_paid_invoices(self):
        db = FakeDB()
        self.assertEqual(AssessedRepository(db).invoice_for_customer(3), [])
        sql = db.c.executed[0][0]
        self.assertIn("WHERE f.klant_id=%s AND f.betaald_op IS NULL", sql)
        self.assertEqual(db.c.executed[0][1], (3,))

    def test_paid_invoice_cannot_overwrite_payment_date(self):
        db = FakeDB(paid=True)
        with self.assertRaises(DomainError):
            AssessedRepository(db).record_payment_action(12, "mark_paid", date(2026, 10, 31))
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.rollbacks, 1)
        self.assertFalse(any("UPDATE Factuur SET betaald_op=" in sql for sql, _ in db.c.executed))

    def test_assessed_sql_examples_mirror_unpaid_invoices_and_retry_time(self):
        sql = (Path(__file__).resolve().parents[1] / "database" / "queries.sql").read_text(encoding="utf-8")
        self.assertIn("WHERE f.klant_id=1 AND f.betaald_op IS NULL", sql)
        self.assertIn("TIME_TO_SEC(lp.geplande_tijd) AS first_attempt_seconds", sql)
        samples = (Path(__file__).resolve().parents[2] / "Documentation" / "Architecture"
                   / "test-data" / "selects_assessed.sql").read_text(encoding="utf-8")
        self.assertIn("WHERE p.opvolging_afgesloten=FALSE AND NOT EXISTS (", samples)
        self.assertIn("WHERE f.klant_id=1 AND f.betaald_op IS NULL", samples)
