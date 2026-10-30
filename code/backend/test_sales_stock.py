"""Check stock without creating an order or inventing reservations."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from repositories.sales_stock_repository import SalesStockRepository
from services.sales_stock_service import SalesStockService


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None
        self.params = None
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, query, params):
        self.statement, self.params = query, params
    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.c = Cursor(rows)
    def cursor(self, dictionary=False):
        assert dictionary
        return self.c


class StockCheckTests(TestCase):
    def setUp(self):
        self.rows = [
            {"product_id": 1, "artikelnummer": "T-1", "productnaam": "Medication A", "voorraad": 3, "gereserveerd": 1, "beschikbaar": 2}
        ]

    def test_query_uses_all_warehouse_locations(self):
        connection = Connection(self.rows)
        self.assertEqual(SalesStockRepository(connection).find_products("T-1"), self.rows)
        self.assertIn("SUM(aantal)", connection.c.statement)
        self.assertIn("FROM Magazijnlocatie", connection.c.statement)
        self.assertIn("FROM Voorraadreservering", connection.c.statement)
        self.assertEqual(connection.c.params, ("%T-1%", "%T-1%"))

    def test_sufficient_and_insufficient_quantity(self):
        repo = type("Repo", (), {"find_products": lambda _, query: self.rows})()
        service = SalesStockService(repo)
        self.assertTrue(service.check("Medication", 2)[0]["voldoende"])
        self.assertFalse(service.check("Medication", 3)[0]["voldoende"])

    def test_get_screen_does_not_change_database(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.rows)):
                response = client.get("/orders?q=Medication&quantity=4")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Onvoldoende voorraad", response.data)
                self.assertIn(b"Gereserveerd", response.data)
            response = client.get("/orders")
            self.assertEqual(response.status_code, 200)
