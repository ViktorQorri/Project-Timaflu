"""Regression checks: AD04/AD05/AD06 keep stock lookup separate from sales entry."""
from unittest import TestCase
from app import create_app

class AssessedScreenTests(TestCase):
    def test_stock_check_links_to_actual_order_entry(self):
        app = create_app()
        source = app.jinja_loader.get_source(app.jinja_env, "orders.html")[0]
        self.assertIn("{% block title %}Voorraad controleren{% endblock %}", source)
        self.assertIn("sales.new_telephone_order", source)
        self.assertIn('form method="get"', source)
        self.assertNotIn("calculate_order_discount", source)
        order_source = app.jinja_loader.get_source(app.jinja_env, "telephone_order.html")[0]
        self.assertIn("form", order_source)

    def test_order_status_lookup_is_available_without_extra_report_page(self):
        app = create_app()
        routes = {rule.rule for rule in app.url_map.iter_rules()}
        self.assertIn("/orders/status", routes)
        self.assertIn("/orders/<int:order_id>/status", routes)
        self.assertNotIn("/reports", routes)
