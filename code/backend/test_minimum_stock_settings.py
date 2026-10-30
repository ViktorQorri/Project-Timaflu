"""Tests for issue #15 configurable minimum-stock warnings."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError, NotFoundError
from repositories.stock_repository import StockRepository
from services.stock_service import StockService


class FakeRepo:
    def __init__(self):
        self.saved = []

    def list_all_minimums(self):
        return [{"product_id": 4, "artikelnummer": "T-04", "productnaam": "Medicijn A",
                 "voorraad": 2, "minimumvoorraad": 10}]

    def set_minimum(self, product_id, minimum):
        self.saved.append((product_id, minimum))


class FakeCursor:
    def __init__(self, found=True):
        self.found = found
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement, params):
        self.statements.append((statement, params))

    def fetchone(self):
        return (4,) if self.found else None


class FakeConnection:
    def __init__(self, found=True):
        self.cursor_instance = FakeCursor(found)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class MinimumStockTests(TestCase):
    def setUp(self):
        self.repo = FakeRepo()
        self.service = StockService(self.repo)

    def test_settings_validation_and_zero(self):
        for bad in ("-1", "2.5", "", "3e2", "abc"):
            with self.assertRaises(DomainError):
                self.service.set_minimum(4, bad)
        self.assertEqual(self.repo.saved, [])
        self.service.set_minimum(4, "0")
        self.service.set_minimum(4, "12")
        self.assertEqual(self.repo.saved, [(4, 0), (4, 12)])

    def test_transaction_with_existing_product(self):
        db = FakeConnection()
        StockRepository(db).set_minimum(4, 7)
        self.assertEqual(db.commits, 1)
        self.assertEqual(db.rollbacks, 0)
        self.assertEqual(db.cursor_instance.statements[-1][1], (7, 4))

    def test_missing_product_rolls_back(self):
        db = FakeConnection(found=False)
        with self.assertRaises(NotFoundError):
            StockRepository(db).set_minimum(9, 10)
        self.assertEqual(db.commits, 0)
        self.assertEqual(db.rollbacks, 1)

    def test_list_settings_and_update_endpoint(self):
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        with patch("routes.purchasing.get_connection", return_value=object()):
            with patch("routes.purchasing.StockService", return_value=self.service):
                with app.test_client() as client:
                    response = client.get("/stock/minimums")
                    self.assertEqual(response.status_code, 200)
                    self.assertIn(b"Medicijn A", response.data)
                    self.assertIn(b"Minimumvoorraad instellen", response.data)
                    response = client.post("/stock/minimums/4",
                                           data={"minimumvoorraad": "15"})
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(self.repo.saved[-1], (4, 15))
