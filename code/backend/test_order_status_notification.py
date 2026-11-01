"""Regression tests for the case-required order status lookup."""
from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch
from app import create_app
from domain.errors import DomainError, NotFoundError
from repositories.order_status_notification_repository import OrderStatusNotificationRepository
from services.order_status_notification_service import OrderStatusNotificationService

class Cursor:
    def __init__(self, order, lines, search_rows):
        self.order, self.lines, self.search_rows = order, lines, search_rows
        self.statements = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params): self.statements.append((query, params))
    def fetchone(self): return self.order
    def fetchall(self):
        return self.lines if "FROM Bestelregel" in self.statements[-1][0] else self.search_rows

class Connection:
    def __init__(self, order=None, lines=(), search_rows=()):
        self.cur = Cursor(order, list(lines), list(search_rows))
    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur

class OrderStatusNotificationTests(TestCase):
    def setUp(self):
        self.order = {
            "bestelling_id": 12, "besteld_op": datetime(2026, 10, 28, 14, 5),
            "gewenste_leverdatum": date(2026, 10, 31), "dagdeel": "ochtend",
            "status_naam": "backorder", "bedrijfsnaam": "Apotheek De Linde",
            "contactpersoon": "Sanne de Vries", "telefoonnummer": "0612345678",
            "afleveradres": "Lindelaan 1, Breda", "afgeleverd_op": None,
        }
        self.lines = [
            {"product_id": 1, "artikelnummer": "T-1", "productnaam": "Paracetamol", "aantal": 10, "gereserveerd": 4},
            {"product_id": 2, "artikelnummer": "T-2", "productnaam": "Ibuprofen", "aantal": 5, "gereserveerd": 5},
        ]
    def service(self, conn):
        return OrderStatusNotificationService(OrderStatusNotificationRepository(conn))
    def test_search(self):
        conn = Connection(search_rows=[self.order])
        found = self.service(conn).search(" Linde ")
        self.assertEqual(conn.cur.statements[0][1], (None, "%Linde%"))
        self.assertEqual(found[0]["status_label"], "Backorder")
        self.service(conn).search("12")
        self.assertEqual(conn.cur.statements[1][1], (12, "%12%"))
    def test_no_empty_or_oversized_query(self):
        conn = Connection()
        self.assertEqual(self.service(conn).search(" "), [])
        with self.assertRaises(DomainError): self.service(conn).search("x" * 101)
        self.assertFalse(conn.cur.statements)
    def test_invalid_and_unknown_id(self):
        for value in ("x", None, 0, -3):
            with self.assertRaises(DomainError): self.service(Connection(self.order)).status_overview(value)
        with self.assertRaises(NotFoundError): self.service(Connection()).status_overview(99)
    def test_backorder_is_status_not_reservation_arithmetic(self):
        result = self.service(Connection(self.order, self.lines)).status_overview(12)
        self.assertTrue(result["has_backorder"])
        self.assertEqual(result["lines"], self.lines)
        self.assertNotIn("backorder", result["lines"][0])
        self.assertNotIn("message", result)
        other = self.service(Connection({**self.order, "status_naam": "wordt verzameld"}, self.lines)).status_overview(12)
        self.assertFalse(other["has_backorder"])
    def test_unknown_status_not_fabricated(self):
        result = self.service(Connection({**self.order, "status_naam": None})).status_overview(12)
        self.assertEqual(result["order"]["status_label"], "Niet geregistreerd")
    def test_delivery_query_and_reservation_query_are_read_only(self):
        conn = Connection(self.order, self.lines)
        self.service(conn).status_overview(12)
        self.assertIn("lp.resultaat = 'afgeleverd'", conn.cur.statements[0][0])
        self.assertIn("LEFT JOIN Voorraadreservering", conn.cur.statements[1][0])
        self.assertEqual([s[1] for s in conn.cur.statements], [(12,), (12,)])
    def test_detail_page_shows_facts_without_invented_backorder_quantity(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, self.lines)):
                response = client.get("/orders/12/status")
            self.assertEqual(response.status_code, 200)
            page = response.get_data(as_text=True)
            self.assertIn("Order in backorder", page)
            self.assertIn("31-10-2026, ochtend", page)
            self.assertIn("Paracetamol", page)
            self.assertNotIn("Backorder: 6", page)
            self.assertNotIn("Bericht voor de klant", page)
            with patch("routes.sales.get_connection", return_value=Connection()):
                self.assertEqual(client.get("/orders/99/status").status_code, 404)
    def test_search_page_and_no_results(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(search_rows=[self.order])):
                response = client.get("/orders?order=Linde")
            self.assertEqual(response.status_code, 200)
            self.assertIn("/orders/12/status", response.get_data(as_text=True))
            with patch("routes.sales.get_connection", return_value=Connection()):
                response = client.get("/orders?order=Onbekend")
            self.assertIn("Geen order gevonden.", response.get_data(as_text=True))
