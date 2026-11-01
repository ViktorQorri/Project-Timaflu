"""Regression tests derived from the official current/desired Timaflu processes."""
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.business import Invoice
from domain.errors import ConflictError, DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.robot_order_repository import RobotOrderRepository
from services.discount_service import DiscountService
from services.order_service import OrderService
from services.product_service import ProductService

from test_discounts import FakeRepository
from test_product_catalog import FakeProductRepository, FakeSupplierRepository, form_data
from test_robot_orders import FakeConnection


class CasusPr123Tests(TestCase):
    def test_weekly_invoice_does_not_merge_individual_order_discount_thresholds(self):
        lines = [
            {"bestelling_id": 21, "quantity": 1, "unit_price": Decimal("400"),
             "besteld_ex_btw": Decimal("400"), "eenmalige_korting_toegepast": False},
            {"bestelling_id": 22, "quantity": 1, "unit_price": Decimal("400"),
             "besteld_ex_btw": Decimal("400"), "eenmalige_korting_toegepast": False},
        ]
        invoice = Invoice(1, "1", date(2026, 10, 30)).createWeeklyInvoice(
            "Apotheek", "Adres", lines, Decimal(0), False
        )
        self.assertEqual(invoice["total_incl_vat"], Decimal("872.00"))
        self.assertEqual(invoice["order_discount"], Decimal("0.00"))
        self.assertEqual(invoice["customer_discount"], Decimal("43.60"))
        self.assertEqual(invoice["total"], Decimal("828.40"))

    def test_partial_delivery_keeps_original_order_discount_threshold(self):
        lines = [{
            "bestelling_id": 21, "quantity": 1, "unit_price": Decimal("100.00"),
            "besteld_ex_btw": Decimal("500.00"), "eenmalige_korting_toegepast": False,
        }]
        invoice = Invoice(1, "1", date(2026, 10, 30)).createWeeklyInvoice(
            "Apotheek", "Adres", lines, Decimal(0), False
        )
        self.assertEqual(invoice["total_incl_vat"], Decimal("109.00"))
        self.assertEqual(invoice["order_discount"], Decimal("5.45"))
        self.assertEqual(invoice["customer_discount"], Decimal("5.18"))
        self.assertEqual(invoice["total"], Decimal("98.37"))

    def test_first_order_discount_is_not_repeated_across_other_orders(self):
        lines = [
            {"bestelling_id": 1, "quantity": 1, "unit_price": Decimal("100"),
             "besteld_ex_btw": Decimal("100"), "eenmalige_korting_toegepast": True},
            {"bestelling_id": 2, "quantity": 1, "unit_price": Decimal("100"),
             "besteld_ex_btw": Decimal("100"), "eenmalige_korting_toegepast": False},
        ]
        invoice = Invoice(1, "1", date(2026, 11, 1)).createWeeklyInvoice(
            "Apotheek", "Adres", lines, Decimal(0), False
        )
        self.assertEqual(invoice["first_order_discount"], Decimal("10.90"))
        self.assertEqual(invoice["total"], Decimal("196.74"))

    def test_cannot_deliver_without_explicit_customer_signature(self):
        for first in (True, False):
            for delivered, signed in ((True, False), (False, True)):
                with self.subTest(first=first, delivered=delivered, signed=signed):
                    with self.assertRaises(DomainError):
                        if first:
                            AssessedRepository(None).register_first_delivery_attempt(
                                5, date(2026, 11, 1), delivered, signed
                            )
                        else:
                            AssessedRepository(None).register_delivery_attempt(
                                5, date(2026, 11, 1), delivered, None, signed
                            )

    def test_delivered_lines_come_from_completed_robot_orders_only(self):
        class Cursor:
            rowcount = 2
            def execute(self, sql, params):
                self.sql, self.params = sql, params
        cursor = Cursor()
        AssessedRepository._record_delivered_lines(cursor, 12)
        self.assertEqual(cursor.params, (12,))
        self.assertIn("JOIN Deelorderregel", cursor.sql)
        self.assertIn("d.afgerond = TRUE", cursor.sql)
        self.assertNotIn("FROM Bestelregel", cursor.sql)

    def test_partial_delivery_stays_backorder_in_database(self):
        class Cursor:
            def execute(self, sql, params):
                self.sql, self.params = sql, params
        cursor = Cursor()
        AssessedRepository._mark_order_after_delivery(cursor, 12)
        self.assertIn("COALESCE(lr.aantal_geleverd, 0) < br.aantal", cursor.sql)
        self.assertIn("THEN 'backorder' ELSE 'afgeleverd'", cursor.sql)
        self.assertEqual(cursor.params, (12,))

    def test_picked_stock_is_decremented_and_reservations_released(self):
        database = FakeConnection()
        RobotOrderRepository(database).complete(1, 20)
        queries = [sql for sql, _ in database.cursor_instance.queries]
        self.assertTrue(any("UPDATE Magazijnlocatie SET aantal = aantal -" in q for q in queries))
        self.assertTrue(any("DELETE FROM Voorraadreservering" in q for q in queries))
        self.assertEqual(database.committed, 1)

    def test_failed_picking_rolls_back_all_inventory_changes(self):
        database = FakeConnection()
        original = database.cursor_instance.fetchall
        def insufficient_stock():
            if "FROM Magazijnlocatie" in database.cursor_instance.current_query:
                return [{"schapnummer": 4, "aantal": 1}]
            return original()
        database.cursor_instance.fetchall = insufficient_stock
        with self.assertRaises(ConflictError):
            RobotOrderRepository(database).complete(1, 20)
        self.assertEqual(database.committed, 0)
        self.assertEqual(database.rolled_back, 1)

    def test_minimum_order_quantity_is_enforced_in_calculation(self):
        class Repository(FakeRepository):
            def find_product(self, product_id):
                return {**super().find_product(product_id), "minimale_bestelhoeveelheid": 5}
        with self.assertRaisesRegex(DomainError, "Bestel minimaal 5"):
            DiscountService(Repository()).calculate_total_amount("7", [("1", "4")])

    def test_new_medicine_requires_management_approval(self):
        repo = FakeProductRepository()
        with self.assertRaisesRegex(DomainError, "directie"):
            ProductService(repo, FakeSupplierRepository()).add_product(
                form_data(management_approved="")
            )
        self.assertIsNone(repo.added)

    def test_urgent_order_must_be_delivered_same_day(self):
        today = date(2026, 11, 1)
        with self.assertRaisesRegex(DomainError, "dezelfde dag"):
            OrderService._delivery_date("2026-11-02", True, today)
        self.assertEqual(OrderService._delivery_date("2026-11-01", True, today), today)

    def test_home_shows_database_unavailable_without_crashing(self):
        from mysql.connector import Error as DatabaseError
        app = create_app()
        app.testing = True
        with app.test_client() as client, patch(
            "routes.home.get_connection", side_effect=DatabaseError("unavailable")
        ):
            response = client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Database niet bereikbaar", response.data)

    def test_frontend_has_no_client_side_javascript(self):
        path = Path(__file__).resolve().parents[1] / "frontend"
        self.assertFalse(list(path.rglob("*.js")))
        for template in (path / "templates").glob("*.html"):
            text = template.read_text(encoding="utf-8-sig").lower()
            self.assertNotIn("<script", text)
