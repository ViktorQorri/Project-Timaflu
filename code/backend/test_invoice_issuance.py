"""Regression checks for the one case-backed weekly invoice issuing process."""
from datetime import date
from decimal import Decimal
from unittest import TestCase

from app import create_app
from domain.business import Invoice
from domain.errors import DomainError
from repositories.weekly_invoice_repository import WeeklyInvoiceRepository


class InvoiceIssuanceTests(TestCase):
    def test_order_discount_is_never_based_on_the_combined_week_amount(self):
        invoice = Invoice(1, "test", date(2026, 10, 30)).createWeeklyInvoiceForOrders(
            "Apotheek", "Adres", [
                {"order_id": 21, "first_order": False, "order_total": Decimal("436"),
                 "customer_discount_percentage": Decimal("5"),
                 "lines": [{"quantity": 1, "unit_price": Decimal("400")}]},
                {"order_id": 22, "first_order": False, "order_total": Decimal("436"),
                 "customer_discount_percentage": Decimal("5"),
                 "lines": [{"quantity": 1, "unit_price": Decimal("400")}]},
            ], annualRevenue=0
        )
        self.assertEqual(invoice["total_incl_vat"], Decimal("872.00"))
        self.assertEqual(invoice["order_discount"], Decimal("0.00"))
        self.assertEqual(invoice["total"], Decimal("828.40"))
        self.assertEqual({row["order_id"] for row in invoice["lines"]}, {21, 22})

    def test_only_the_original_first_order_gets_the_ten_percent_discount(self):
        invoice = Invoice(1, "test", date(2026, 10, 30)).createWeeklyInvoiceForOrders(
            "Apotheek", "Adres", [
                {"order_id": 21, "first_order": True, "order_total": Decimal("109"),
                 "customer_discount_percentage": Decimal("5"),
                 "lines": [{"quantity": 1, "unit_price": Decimal("100")}]},
                {"order_id": 22, "first_order": False, "order_total": Decimal("109"),
                 "customer_discount_percentage": Decimal("5"),
                 "lines": [{"quantity": 1, "unit_price": Decimal("100")}]},
            ], annualRevenue=0
        )
        self.assertEqual(invoice["first_order_discount"], Decimal("10.90"))
        self.assertEqual(invoice["total"], Decimal("196.74"))

    def test_invoice_week_must_have_fully_ended_and_sender_must_be_known(self):
        week = date(2026, 10, 19)
        WeeklyInvoiceRepository.validate_week(week, date(2026, 10, 30), "Teststraat 1")
        with self.assertRaisesRegex(DomainError, "afgesloten week"):
            WeeklyInvoiceRepository.validate_week(week, date(2026, 10, 24), "Teststraat 1")
        with self.assertRaisesRegex(DomainError, "maandag"):
            WeeklyInvoiceRepository.validate_week(
                date(2026, 10, 20), date(2026, 10, 30), "Teststraat 1"
            )
        with self.assertRaisesRegex(DomainError, "afzenderadres"):
            WeeklyInvoiceRepository.validate_week(week, date(2026, 10, 30), "")

    def test_only_the_canonical_weekly_route_can_create_invoices(self):
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="test")
        issuing_routes = [
            rule.rule for rule in app.url_map.iter_rules()
            if rule.rule.startswith("/invoices") and "POST" in rule.methods
        ]
        self.assertIn("/invoices/weekly", issuing_routes)
        self.assertNotIn("/invoices/create", issuing_routes)
        with app.test_client() as client:
            old = client.post(
                "/invoices/create",
                data={"customer_id": "1", "week_of": "2026-10-30"}
            )
            self.assertEqual(old.status_code, 404)
            unapproved = client.post(
                "/invoices/weekly", data={"week_start": "2026-10-19"}
            )
            self.assertEqual(unapproved.status_code, 400)
            self.assertIn(b"Controleer en bevestig", unapproved.data)

    def test_unissued_or_empty_week_cannot_create_fake_invoice_amounts(self):
        invoice = Invoice(1, "test", date(2026, 10, 30))
        with self.assertRaises(DomainError):
            invoice.createWeeklyInvoiceForOrders(
                "Apotheek", "Adres", [], annualRevenue=0
            )
