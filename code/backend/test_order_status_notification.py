"""Order status for informing the customer; nothing is sent and the database is not changed."""

from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError, NotFoundError
from repositories.order_status_notification_repository import OrderStatusNotificationRepository
from services.order_status_notification_service import OrderStatusNotificationService


class Cursor:
    def __init__(self, order, lines, search_rows):
        self.order = order
        self.lines = lines
        self.search_rows = search_rows
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.statements.append((query, params))

    def fetchone(self):
        return self.order

    def fetchall(self):
        return self.lines if "FROM Bestelregel" in self.statements[-1][0] else self.search_rows


class Connection:
    """Has no commit(), so any attempt to write fails the test."""

    def __init__(self, order=None, lines=(), search_rows=()):
        self.cur = Cursor(order, list(lines), list(search_rows))

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur


class OrderStatusNotificationTests(TestCase):
    def setUp(self):
        self.order = {
            "bestelling_id": 12,
            "besteld_op": datetime(2026, 10, 28, 14, 5),
            "gewenste_leverdatum": date(2026, 10, 31),
            "dagdeel": "ochtend",
            "status_naam": "backorder",
            "bedrijfsnaam": "Apotheek De Linde",
            "contactpersoon": "Sanne de Vries",
            "telefoonnummer": "0612345678",
            "afleveradres": "Lindelaan 1, Breda",
            "afgeleverd_op": None,
        }
        self.lines = [
            {"product_id": 1, "artikelnummer": "T-1", "productnaam": "Paracetamol", "aantal": 10, "gereserveerd": 4},
            {"product_id": 2, "artikelnummer": "T-2", "productnaam": "Ibuprofen", "aantal": 5, "gereserveerd": 5},
        ]
        self.search_rows = [
            {"bestelling_id": 12, "bedrijfsnaam": "Apotheek De Linde", "besteld_op": datetime(2026, 10, 28, 14, 5),
             "gewenste_leverdatum": date(2026, 10, 31), "dagdeel": "ochtend", "status_naam": "wordt verzameld"},
        ]

    def service(self, connection):
        return OrderStatusNotificationService(OrderStatusNotificationRepository(connection))

    def test_search_by_name_uses_parameters_and_no_order_number(self):
        connection = Connection(search_rows=self.search_rows)
        rows = self.service(connection).search("  Linde ")
        query, params = connection.cur.statements[0]
        self.assertEqual(params, (None, "%Linde%"))
        self.assertIn("JOIN Klant", query)
        self.assertEqual(rows[0]["status_label"], "Wordt verzameld")
        self.assertEqual(rows[0]["status_tone"], "info")

    def test_search_by_order_number(self):
        connection = Connection(search_rows=self.search_rows)
        self.service(connection).search("12")
        self.assertEqual(connection.cur.statements[0][1], (12, "%12%"))

    def test_empty_search_does_not_query_database(self):
        connection = Connection()
        self.assertEqual(self.service(connection).search("   "), [])
        self.assertEqual(connection.cur.statements, [])

    def test_too_long_search_is_rejected(self):
        connection = Connection()
        with self.assertRaises(DomainError):
            self.service(connection).search("x" * 101)
        self.assertEqual(connection.cur.statements, [])

    def test_invalid_order_number_rejected_before_query(self):
        for value in ("x", None, 0, -3):
            connection = Connection(self.order)
            with self.assertRaises(DomainError):
                self.service(connection).status_overview(value)
            self.assertEqual(connection.cur.statements, [])

    def test_unknown_order_raises_not_found(self):
        with self.assertRaises(NotFoundError):
            self.service(Connection(order=None)).status_overview(99)

    def test_status_and_delivery_date_visible_in_message(self):
        result = self.service(Connection(self.order, self.lines)).status_overview("12")
        self.assertEqual(result["order"]["status_label"], "Backorder")
        self.assertEqual(result["order"]["status_tone"], "warning")
        self.assertIn("Beste Sanne de Vries,", result["message"])
        self.assertIn("heeft de status 'backorder'", result["message"])
        self.assertIn("De geplande levering is op 31-10-2026 in de ochtend.", result["message"])

    def test_backorder_quantity_is_ordered_minus_reserved(self):
        result = self.service(Connection(self.order, self.lines)).status_overview(12)
        self.assertEqual([line["backorder"] for line in result["lines"]], [6, 0])
        self.assertEqual(len(result["backorder_lines"]), 1)
        self.assertIn("in backorder: 6x Paracetamol", result["message"])

    def test_no_backorder_when_order_is_not_in_backorder(self):
        order = {**self.order, "status_naam": "wordt verzameld"}
        result = self.service(Connection(order, self.lines)).status_overview(12)
        self.assertEqual(result["backorder_lines"], [])
        self.assertNotIn("backorder", result["message"])

    def test_delivered_order_shows_actual_delivery_date(self):
        order = {**self.order, "status_naam": "afgeleverd", "afgeleverd_op": date(2026, 10, 31)}
        result = self.service(Connection(order, self.lines)).status_overview(12)
        self.assertEqual(result["order"]["status_tone"], "success")
        self.assertIn("De bestelling is afgeleverd op 31-10-2026.", result["message"])

    def test_order_without_status(self):
        order = {**self.order, "status_naam": None, "contactpersoon": None}
        result = self.service(Connection(order, [])).status_overview(12)
        self.assertEqual(result["order"]["status_label"], "Nog geen status")
        self.assertIn("Beste Apotheek De Linde,", result["message"])
        self.assertIn("is ontvangen en wordt verwerkt.", result["message"])

    def test_repository_reads_delivery_and_reservations(self):
        connection = Connection(self.order, self.lines)
        self.service(connection).status_overview(12)
        order_query, order_params = connection.cur.statements[0]
        lines_query, lines_params = connection.cur.statements[1]
        self.assertEqual(order_params, (12,))
        self.assertIn("lp.resultaat = 'afgeleverd'", order_query)
        self.assertEqual(lines_params, (12,))
        self.assertIn("LEFT JOIN Voorraadreservering", lines_query)

    def test_status_page_shows_status_delivery_date_and_backorder(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(self.order, self.lines)):
                response = client.get("/orders/12/status")
            self.assertEqual(response.status_code, 200)
            page = response.get_data(as_text=True)
            self.assertIn("Order 12", page)
            self.assertIn("Backorder: 6", page)
            self.assertIn("31-10-2026, ochtend", page)
            self.assertIn("Bericht voor de klant", page)
            with patch("routes.sales.get_connection", return_value=Connection(order=None)):
                self.assertEqual(client.get("/orders/99/status").status_code, 404)

    def test_orders_page_lists_found_orders_and_empty_state(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=Connection(search_rows=self.search_rows)):
                response = client.get("/orders?order=Linde")
            self.assertEqual(response.status_code, 200)
            page = response.get_data(as_text=True)
            self.assertIn("Apotheek De Linde", page)
            self.assertIn("Wordt verzameld", page)
            self.assertIn("/orders/12/status", page)
            with patch("routes.sales.get_connection", return_value=Connection()):
                response = client.get("/orders?order=Onbekend")
            self.assertIn("Geen order gevonden.", response.get_data(as_text=True))
