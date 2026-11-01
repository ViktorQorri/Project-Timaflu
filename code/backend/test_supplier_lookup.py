"""Focused tests for the supplier list required by purchasing."""

from unittest import TestCase
from unittest.mock import patch
from decimal import Decimal

from app import create_app
from repositories.supplier_repository import SupplierRepository
from services.supplier_service import SupplierService


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.sql = None
        self.params = None
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, sql, params):
        self.sql, self.params = sql, params
    def fetchall(self):
        return self.rows


class Connection:
    def __init__(self, rows):
        self.cur = Cursor(rows)
    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


class SupplierLookupTests(TestCase):
    def setUp(self):
        self.rows = [
            {"product_id": 1, "productnaam": "Medication A", "leverancier_id": 3, "leverancier": "Supplier A", "contactpersoon": "Anna", "telefoonnummer": "123", "internetadres": "https://bestellen.example", "inkoopprijs": Decimal("2.50")}
        ]

    def test_repository_orders_offers_by_price_and_uses_parameter(self):
        connection = Connection(self.rows)
        self.assertEqual(SupplierRepository(connection).find_offers("Medication"), self.rows)
        self.assertEqual(connection.cur.params, ("%Medication%",))
        self.assertIn("a.inkoopprijs ASC", connection.cur.sql)
        self.assertIn("JOIN LeveranciersAanbod", connection.cur.sql)
        self.assertIn("l.internetadres", connection.cur.sql)
        self.assertIn("p.in_assortiment = TRUE", connection.cur.sql)

    def test_empty_search_does_not_query_database(self):
        class NoQuery:
            def find_offers(self, value):
                raise AssertionError("should not run")
        self.assertEqual(SupplierService(NoQuery()).offers_for_product("  "), [])

    def test_supplier_page_renders_results(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.purchasing.get_connection", return_value=Connection(self.rows)):
                response = client.get("/suppliers?product=Medication")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Supplier A", response.data)
                self.assertIn(b"Anna", response.data)
                self.assertIn(b"https://bestellen.example", response.data)
                self.assertIn(b"2,50", response.data)
                self.assertIn(b"/suppliers/remove-offer", response.data)
                self.assertIn(b'name="confirmed"', response.data)
                self.assertIn(b"/products/1/remove", response.data)
            with patch("routes.purchasing.get_connection", return_value=Connection([])):
                response = client.get("/suppliers?product=Unknown")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Geen leveranciers gevonden", response.data)
                self.assertIn(b"zonder leverancier kan het niet worden bijbesteld", response.data)
                self.assertNotIn(b"Bevestigde order vastleggen", response.data)
