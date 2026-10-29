"""Tests for the stock shortage feature, without requiring a live MySQL server."""

from unittest import TestCase
from unittest.mock import patch
from decimal import Decimal

from app import create_app
from repositories.stock_repository import StockRepository
from services.stock_service import StockService


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql):
        self.sql = sql

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.cursor_instance = FakeCursor(rows)

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cursor_instance


class StockShortageTests(TestCase):
    def setUp(self):
        self.rows = [
            {
                "product_id": 4,
                "artikelnummer": "TIM-4",
                "productnaam": "Medicine A",
                "minimumvoorraad": 12,
                "voorraad": Decimal("4"),
            },
        ]

    def test_repository_uses_current_warehouse_inventory_and_includes_zero_locations(self):
        connection = FakeConnection(self.rows)
        self.assertEqual(StockRepository(connection).list_stock_below_minimum(), self.rows)
        self.assertIn("LEFT JOIN Magazijnlocatie", connection.cursor_instance.sql)
        self.assertIn("HAVING voorraad < p.minimumvoorraad", connection.cursor_instance.sql)

    def test_service_calculates_shortage(self):
        class Repo:
            def list_stock_below_minimum(self):
                return self_rows

        self_rows = self.rows
        self.assertEqual(StockService(Repo()).shortages()[0]["tekort"], Decimal("8"))

    def test_stock_page_renders_data_and_empty_state(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.purchasing.get_connection", return_value=FakeConnection(self.rows)):
                response = client.get("/stock")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Medicine A", response.data)
                self.assertIn(b"TIM-4", response.data)
            with patch("routes.purchasing.get_connection", return_value=FakeConnection([])):
                response = client.get("/stock")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"No stock shortages", response.data)
