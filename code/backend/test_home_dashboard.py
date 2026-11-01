"""The home screen links employees to every supported work process."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app


class HomeDashboardTests(TestCase):
    def test_home_page_lists_workflows_and_database_status(self):
        app = create_app()
        app.testing = True

        with app.test_client() as client:
            with patch("routes.home.get_connection", return_value=object()), patch(
                "routes.home.HealthService.database_is_reachable", return_value=True
            ):
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        for href in (
            "/customers",
            "/orders/new",
            "/orders",
            "/products",
            "/stock",
            "/suppliers",
            "/manufacturers",
            "/reorder",
            "/order-picking",
            "/deliveries",
            "/invoices",
            "/reports",
            "/acquisition",
        ):
            with self.subTest(href=href):
                self.assertIn(f'href="{href}"'.encode(), response.data)
        self.assertIn(b"Database verbonden", response.data)
        self.assertIn(b"Direct naar de inhoud", response.data)

    def test_home_page_shows_database_unavailable_status(self):
        app = create_app()
        app.testing = True

        with app.test_client() as client:
            with patch("routes.home.get_connection", return_value=object()), patch(
                "routes.home.HealthService.database_is_reachable", return_value=False
            ):
                response = client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Database niet bereikbaar", response.data)

    def test_shared_stylesheet_is_served(self):
        app = create_app()
        app.testing = True

        with app.test_client() as client:
            response = client.get("/static/css/operations.css")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b".home-workflows", response.data)
        response.close()
