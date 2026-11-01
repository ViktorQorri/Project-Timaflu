"""Tests for status information prepared for sales employees and customers."""

from datetime import date, datetime
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError, NotFoundError
from services.order_status_notification_service import (
    OrderStatusNotificationService,
)


class Repository:
    def search_orders(self, order_id, customer_name):
        self.search_args = (order_id, customer_name)
        return [{
            "bestelling_id": 7,
            "bedrijfsnaam": "Apotheek A",
            "besteld_op": datetime(2026, 10, 29, 10, 0),
            "gewenste_leverdatum": date(2026, 10, 31),
            "dagdeel": "ochtend",
            "status_naam": "backorder",
        }]

    def find_order(self, order_id):
        self.order_id = order_id
        return {
            "bestelling_id": order_id,
            "bedrijfsnaam": "Apotheek A",
            "contactpersoon": "Contact A",
            "telefoonnummer": "0612345678",
            "besteld_op": datetime(2026, 10, 29, 10, 0),
            "gewenste_leverdatum": date(2026, 10, 31),
            "dagdeel": "ochtend",
            "status_naam": "backorder",
            "afgeleverd_op": None,
        }

    def find_order_lines(self, order_id):
        self.line_order_id = order_id
        return [
            {
                "product_id": 3,
                "artikelnummer": "MED-3",
                "productnaam": "Medicijn A",
                "aantal": 8,
                "gereserveerd": 5,
            },
        ]


class OrderStatusNotificationTests(TestCase):
    def setUp(self):
        self.repository = Repository()
        self.service = OrderStatusNotificationService(self.repository)

    def test_search_matches_number_or_customer_and_labels_status(self):
        orders = self.service.search("7")
        self.assertEqual(self.repository.search_args, (7, "7"))
        self.assertEqual(orders[0]["status_label"], "Backorder")
        self.assertEqual(orders[0]["status_tone"], "warning")

    def test_empty_or_overlong_search(self):
        self.assertEqual(self.service.search(" "), [])
        with self.assertRaises(DomainError):
            self.service.search("x" * 101)

    def test_backorder_quantities_and_customer_message(self):
        result = self.service.status_overview("7")
        self.assertEqual(result["lines"][0]["backorder"], 3)
        self.assertIn("3x Medicijn A", result["message"])
        self.assertIn("geplande levering", result["message"])
        self.assertEqual(self.repository.line_order_id, 7)

    def test_invalid_or_missing_order(self):
        for value in ("abc", 0):
            with self.assertRaises(DomainError):
                self.service.status_overview(value)

        class MissingOrder(Repository):
            def find_order(self, order_id):
                return None

        with self.assertRaises(NotFoundError):
            OrderStatusNotificationService(MissingOrder()).status_overview(99)

    def test_order_search_and_status_page_render(self):
        app = create_app()
        app.config["TESTING"] = True
        with patch(
            "routes.sales.OrderStatusNotificationService",
            return_value=self.service,
        ), patch("routes.sales.get_connection", return_value=object()):
            with app.test_client() as client:
                search = client.get("/orders")
                detail = client.get("/orders/7/status")
        self.assertEqual(search.status_code, 200)
        self.assertIn(b"Bestaande bestellingen en hun status", search.data)
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Geplande levering", detail.data)
        self.assertIn(b"Backorder", detail.data)
        self.assertIn(b"Bericht voor de klant", detail.data)
