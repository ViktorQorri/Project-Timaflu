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
            {"product_id": 1, "productnaam": "Medication A", "leverancier": "Supplier A", "contactpersoon": "Anna", "telefoonnummer": "123", "inkoopprijs": Decimal("2.50")}
        ]

    def test_repository_orders_offers_by_price_and_uses_parameter(self):
        connection = Connection(self.rows)
        self.assertEqual(SupplierRepository(connection).find_offers("Medication"), self.rows)
        self.assertEqual(connection.cur.params, ("Medication",))
        self.assertIn("p.productnaam = %s", connection.cur.sql)
        self.assertNotIn("LIKE", connection.cur.sql)
        self.assertIn("a.inkoopprijs ASC", connection.cur.sql)
        self.assertIn("JOIN LeveranciersAanbod", connection.cur.sql)

    def test_product_id_prevents_other_similarly_named_medicines(self):
        connection = Connection(self.rows)
        self.assertEqual(SupplierRepository(connection).find_offers(product_id=17), self.rows)
        self.assertEqual(connection.cur.params, (17,))
        self.assertIn("p.product_id = %s", connection.cur.sql)
        self.assertNotIn("LIKE", connection.cur.sql)

    def test_manual_search_uses_literal_parameter_and_returns_product_identity(self):
        products = [{"product_id": 1, "productnaam": "Medication A", "artikelnummer": "MED-1"}]
        connection = Connection(products)
        self.assertEqual(SupplierRepository(connection).search_products_by_name("Medication %_"), products)
        self.assertEqual(connection.cur.params, ("Medication %_",))
        self.assertIn("LOCATE(%s, p.productnaam) > 0", connection.cur.sql)
        self.assertIn("p.in_assortiment = TRUE", connection.cur.sql)
        self.assertIn("p.artikelnummer", connection.cur.sql)

    def test_empty_manual_search_does_not_query_database(self):
        class NoQuery:
            def search_products_by_name(self, name):
                raise AssertionError("should not query")
        self.assertEqual(SupplierService(NoQuery()).products_matching_name("  "), [])

    def test_empty_search_does_not_query_database(self):
        class NoQuery:
            def find_offers(self, value):
                raise AssertionError("should not run")
        self.assertEqual(SupplierService(NoQuery()).offers_for_product("  "), [])

    def test_manual_search_requires_explicit_product_selection(self):
        products = [
            {"product_id": 1, "productnaam": "Medication A", "artikelnummer": "MED-1"},
            {"product_id": 3, "productnaam": "Medication A", "artikelnummer": "MED-3"},
        ]
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.purchasing.get_connection", return_value=Connection(products)) as db:
                response = client.get("/suppliers?product=Medication")
                self.assertEqual(response.status_code, 200)
                html = response.get_data(as_text=True)
                self.assertIn("Kies het juiste medicijn", html)
                self.assertIn("MED-1", html)
                self.assertIn("MED-3", html)
                self.assertIn("product_id=1", html)
                self.assertIn("product_id=3", html)
                self.assertNotIn("Bevestigde order vastleggen", html)
                self.assertEqual(db.return_value.cur.params, ("Medication",))

    def test_supplier_page_renders_only_selected_product_offers(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.purchasing.get_connection", return_value=Connection(self.rows)) as connection:
                response = client.get("/suppliers?product_id=1")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Supplier A", response.data)
                self.assertIn(b"Anna", response.data)
                self.assertIn(b"Bevestigde order vastleggen", response.data)
                self.assertEqual(connection.return_value.cur.params, (1,))
                invalid = client.get("/suppliers?product_id=abc")
                self.assertEqual(invalid.status_code, 400)
            with patch("routes.purchasing.get_connection", return_value=Connection([])):
                response = client.get("/suppliers?product=Unknown")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Geen medicijnen gevonden", response.data)
                response = client.get("/suppliers?product_id=999")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Geen leveranciers gevonden", response.data)
