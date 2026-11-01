"""Trace AD01-AD28: the homepage navigates to the current supported workflows."""
from unittest import TestCase
from unittest.mock import patch
from app import create_app

class HomeDashboardTests(TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.testing = True

    def test_home_page_lists_supported_workflows(self):
        with self.app.test_client() as client:
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        for href in ("/customers", "/orders/new", "/orders", "/products", "/stock",
                     "/suppliers", "/manufacturers", "/reorder", "/order-picking",
                     "/deliveries", "/invoices", "/acquisition"):
            with self.subTest(href=href):
                self.assertIn(('href="'+href+'"').encode(), response.data)
        self.assertIn(b"Direct naar de inhoud", response.data)
        self.assertIn(b"mobile-navigation", response.data)

    def test_home_page_has_no_database_dependency(self):
        # The present homepage is static; a disconnected DB must not block navigation.
        with patch("db.get_connection", side_effect=RuntimeError("offline")):
            with self.app.test_client() as client:
                response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Overzicht van je werkprocessen", response.data)

    def test_shared_stylesheet_is_served(self):
        with self.app.test_client() as client:
            response = client.get("/static/css/operations.css")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b".home-workflows", response.data)
        response.close()
