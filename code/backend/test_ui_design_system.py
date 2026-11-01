"""Protect the Timaflu design contract across all Flask/Jinja screens.

Visual rules follow the supplied design system. No frontend JavaScript,
invented user roles or demonstration credentials are required by the case.
"""
from pathlib import Path
from contextlib import ExitStack
from unittest import TestCase
from unittest.mock import patch

from app import create_app

ROOT = Path(__file__).resolve().parents[1] / "frontend"
TEMPLATES = ROOT / "templates"
STYLES = ROOT / "static" / "css"


class DesignSystemTests(TestCase):
    def test_shared_design_tokens_and_fonts(self):
        css = (STYLES / "ui-system.css").read_text(encoding="utf-8")
        for token in (
            "--navy: #123653",
            "--blue: #0f70b7",
            "--sky: #eaf5fb",
            "--muted: #6d8292",
            "--line: #dce8ef",
            "--bg: #f5f8fa",
            "#267e55",
            "#ae6a18",
            "#bd4646",
            "Manrope",
            "DM Sans",
            "@media (max-width: 1100px)",
            "@media (max-width: 760px)",
            "@media (max-width: 430px)",
        ):
            self.assertIn(token, css)
        self.assertTrue((STYLES / "ui-system.css").is_file())

    def test_all_screens_use_the_same_base_without_javascript(self):
        app = create_app()
        templates = sorted(TEMPLATES.glob("*.html"))
        self.assertGreaterEqual(len(templates), 20)
        for file in templates:
            source = file.read_text(encoding="utf-8")
            app.jinja_env.get_template(file.name)
            self.assertNotIn("<script", source.lower(), file.name)
            self.assertNotIn("onclick=", source.lower(), file.name)
            if file.name != "base.html":
                self.assertIn('extends "base.html"', source, file.name)
        base = (TEMPLATES / "base.html").read_text(encoding="utf-8")
        self.assertIn("css/ui-system.css", base)
        self.assertIn("<details class=\"mobile-navigation\">", base)
        self.assertIn('class="brand-mark"', base)

    def test_dashboard_and_mobile_process_layout(self):
        app = create_app()
        app.config.update(TESTING=True)
        with ExitStack() as stack:
            for name in ("home", "order_picking", "distribution", "acquisition",
                         "sales", "administration", "reports"):
                stack.enter_context(patch(f"routes.{name}.get_connection", return_value=object()))

            stack.enter_context(patch("routes.home.HealthService"))
            customer_service=stack.enter_context(patch("routes.sales.customer_service"))
            customer_service.return_value.overview.return_value=[]

            picking=stack.enter_context(patch("routes.order_picking.PickingBinService"))
            picking.return_value.bins.return_value=[]
            robot=stack.enter_context(patch("routes.order_picking.RobotOrderRepository"))
            robot.return_value.orders_ready_for_dispatch.return_value=[]

            distribution=stack.enter_context(patch("routes.distribution.DistributionService"))
            distribution.return_value.orders_with_bins.return_value=[]
            distribution.return_value.orders_to_schedule.return_value=[]
            distribution.return_value.couriers.return_value=[]
            deliveries=stack.enter_context(patch("routes.distribution.AssessedRepository"))
            deliveries.return_value.delivery_schedule.return_value=[]

            acquisition=stack.enter_context(patch("routes.acquisition._service"))
            acquisition.return_value.due_follow_ups.return_value=[]

            admin=stack.enter_context(patch("routes.administration.AssessedRepository"))
            admin.return_value.outstanding_purchase_invoices.return_value=[]
            admin.return_value.uninvoiced_deliveries.return_value=[]

            report=stack.enter_context(patch("routes.reports.OrderStatusReportRepository"))
            report.return_value.list_orders.return_value=[]

            with app.test_client() as client:
                for route in ("/", "/customers", "/orders", "/order-picking",
                              "/deliveries", "/invoices", "/acquisition", "/reports"):
                    response=client.get(route)
                    self.assertEqual(response.status_code,200,route)
                    self.assertIn(b"ui-system.css",response.data,route)
                    self.assertIn(b"mobile-navigation",response.data,route)
                    self.assertIn(b"main-content",response.data,route)
