"""Guard existing reports and order discount UI in the assessed scenarios PR."""
from unittest import TestCase
from app import create_app

class AssessedScreenTests(TestCase):
    def test_order_form_appears_only_in_content(self):
        app = create_app()
        page = app.jinja_env.get_template("orders.html")
        source = (app.jinja_loader.get_source(app.jinja_env, "orders.html"))[0]
        self.assertIn("{% block title %}Voorraad controleren{% endblock %}", source)
        self.assertEqual(source.count("calculate_order_discount"), 1)
        self.assertEqual(source.count('<form method="post"'), 1)

    def test_reports_route_kept_for_reporting_prs(self):
        app = create_app()
        app.config["TESTING"] = True
        with app.test_client() as client:
            response = client.get("/reports")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Rapportages", response.data)
