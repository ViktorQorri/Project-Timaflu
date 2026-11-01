"""PR #99 annual-discount and first-order integration against disposable MySQL only.

Requires explicit TIMAFLU_TEST_ALLOW_RESET=isolated and loopback MySQL test settings.
No existing database or production records are modified.
"""
from datetime import date
from decimal import Decimal
import re
import os
from pathlib import Path
import unittest

import mysql.connector

from app import create_app
from domain.errors import ConflictError, DomainError
from repositories.discount_repository import DiscountRepository
from services.discount_service import DiscountService

ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "timaflu_pr99_annual_test"


@unittest.skipUnless(
    os.getenv("TIMAFLU_TEST_ALLOW_RESET") == "isolated"
    and os.getenv("TIMAFLU_TEST_MYSQL_HOST") == "127.0.0.1",
    "Requires explicitly isolated loopback MySQL test database",
)
class AnnualDiscountMySqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.opts = dict(
            host="127.0.0.1",
            port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
            user=os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
            password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        )

    def setUp(self):
        admin = mysql.connector.connect(**self.opts)
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
                cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4")
            admin.commit()
        finally:
            admin.close()

        self.db = mysql.connector.connect(**self.opts, database=DB_NAME)
        script = "\n".join(
            line for line in (ROOT / "code/database/schema.sql")
            .read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("--")
        )
        with self.db.cursor() as cursor:
            for statement in script.split(";"):
                if statement.strip():
                    cursor.execute(statement)
            cursor.execute("INSERT INTO Adres (adres) VALUES ('Fictieve teststraat 1')")
            cursor.execute("""
                INSERT INTO Klant (bedrijfsnaam, afleveradres_id, betaaladres_id)
                VALUES ('Onder grens', 1, 1), ('Op grens', 1, 1),
                       ('Hoge omzet', 1, 1), ('Nieuwe apotheek', 1, 1)
            """)
            cursor.execute("""
                INSERT INTO Factuur (klant_id, factuurdatum, betaald_op, totaal_bedrag)
                VALUES (1, '2025-10-01', '2025-11-01', 9999.99),
                       (1, '2025-12-10', NULL, 500000.00),
                       (1, '2024-08-01', '2024-08-04', 500000.00),
                       (2, '2025-12-01', '2025-12-11', 10000.00),
                       (3, '2025-12-15', '2025-12-31', 20000.00)
            """)
            cursor.execute("""
                INSERT INTO Product (artikelnummer, bestelcode, productnaam,
                                     prijs_per_grootverpakking, aantal_detailverpakkingen,
                                     minimale_bestelhoeveelheid, minimumvoorraad)
                VALUES ('T99', 'T99', 'Testmedicijn', 100.00, 1, 1, 1)
            """)
            cursor.execute("""
                INSERT INTO Magazijnlocatie (gang, schapnummer, product_id, aantal)
                VALUES ('A', 1, 1, 100)
            """)
        self.db.commit()
        self.discount_repo = DiscountRepository(self.db)
        self.service = DiscountService(self.discount_repo)
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SECRET_KEY="pr99-isolated-test",
            DB_HOST="127.0.0.1",
            DB_PORT=self.opts["port"],
            DB_NAME=DB_NAME,
            DB_USER=self.opts["user"],
            DB_PASSWORD=self.opts["password"],
        )

    def tearDown(self):
        self.db.close()
        admin = mysql.connector.connect(**self.opts)
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
            admin.commit()
        finally:
            admin.close()

    def rows(self, query, params=()):
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def test_december_31_stores_paid_year_rates_then_orders_use_them(self):
        result = self.service.update_annual_discounts(date(2025, 12, 31))
        self.assertEqual(result, {"discount_year": 2026, "customers": 4})
        self.assertEqual({
            row["klant_id"]: row["percentage"] for row in self.rows(
                "SELECT klant_id, percentage FROM Klantkorting WHERE kalenderjaar = 2026"
            )
        }, {1: Decimal("5"), 2: Decimal("10"),
            3: Decimal("15"), 4: Decimal("5")})

        # Repeating the year-end job does not duplicate or change recorded rates.
        self.service.update_annual_discounts(date(2025, 12, 31))
        self.assertEqual(
            len(self.rows("SELECT klant_id FROM Klantkorting WHERE kalenderjaar=2026")), 4
        )

        # Changes to previous-year invoices must not affect the already fixed 2026 rate.
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Factuur (klant_id, factuurdatum, betaald_op, totaal_bedrag)
                VALUES (1, '2025-12-30', '2025-12-31', 30000.00)
            """)
        self.db.commit()
        quote = self.service.calculate_total_amount(1, [(1, 10)], date(2026, 11, 1))
        self.assertEqual(quote["customer_discount_percentage"], Decimal("5"))
        self.assertEqual(quote["total_amount"], Decimal("885.35"))
        self.assertTrue(quote["one_time_discount"])

        # The actual order-entry route applies and persists the one-time allowance.
        with self.app.test_client() as client:
            preview = client.get("/orders/new?customer_id=2&product_id=1&quantity=10")
            self.assertEqual(preview.status_code, 200, preview.data[:600])
            self.assertIn(b"Klantenkorting 2026: 10%", preview.data)
            approved_quote = re.search(
                rb'name="quote" value="([^"]+)"', preview.data
            ).group(1).decode("ascii")
            order = client.post("/orders/new", data={
                "customer_id": "2", "product_id": "1", "quantity": "10",
                "delivery_date": "2099-01-05", "part_of_day": "ochtend",
                "quote": approved_quote,
            })
            self.assertEqual(order.status_code, 302, order.data[:600])
        self.db.commit()
        applied = self.rows(
            "SELECT eenmalige_korting_toegepast AS applied FROM Bestelling WHERE klant_id=2"
        )
        self.assertEqual([r["applied"] for r in applied], [1])
        # The test connection has its own REPEATABLE READ snapshot.
        self.db.commit()
        next_quote = self.service.calculate_total_amount(2, [(1, 1)], date(2026, 11, 1))
        self.assertFalse(next_quote["one_time_discount"])
        self.assertEqual(next_quote["customer_discount_percentage"], Decimal("10"))

    def test_new_customer_gets_five_percent_fixed_when_first_order_saved(self):
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Klant (bedrijfsnaam, afleveradres_id, betaaladres_id,
                                   eenmalige_korting_toegezegd)
                VALUES ('Later toegevoegd', 1, 1, FALSE)
            """)
            new_customer = cursor.lastrowid
        self.db.commit()
        self.assertEqual(self.discount_repo.get_customer_discount_percentage(
            new_customer, 2026
        ), None)
        with self.app.test_client() as client:
            preview = client.get(
                f"/orders/new?customer_id={new_customer}&product_id=1&quantity=1"
            )
            self.assertEqual(preview.status_code, 200)
            approved_quote = re.search(
                rb'name="quote" value="([^"]+)"', preview.data
            ).group(1).decode("ascii")
            response = client.post("/orders/new", data={
                "customer_id": str(new_customer), "product_id": "1", "quantity": "1",
                "delivery_date": "2099-01-05", "part_of_day": "middag",
                "quote": approved_quote,
            })
            self.assertEqual(response.status_code, 302, response.data[:600])
        self.db.commit()
        self.assertEqual(self.discount_repo.get_customer_discount_percentage(
            new_customer, 2026
        ), Decimal("5"))
        self.assertEqual(self.rows("""
            SELECT eenmalige_korting_toegepast AS applied FROM Bestelling
            WHERE klant_id = %s
        """, (new_customer,))[0]["applied"], 1)

    def test_changing_warehouse_stock_after_customer_approval_blocks_order(self):
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)
                VALUES (1, %s, 5.00)
            """, (date.today().year,))
        self.db.commit()
        with self.app.test_client() as client:
            preview = client.get("/orders/new?customer_id=1&product_id=1&quantity=10")
            self.assertEqual(preview.status_code, 200)
            approved_quote = re.search(
                rb'name="quote" value="([^"]+)"', preview.data
            ).group(1).decode("ascii")

            with self.db.cursor() as cursor:
                cursor.execute("""
                    UPDATE Magazijnlocatie SET aantal = 99
                    WHERE gang = 'A' AND schapnummer = 1
                """)
            self.db.commit()
            response = client.post("/orders/new", data={
                "customer_id": "1", "product_id": "1", "quantity": "10",
                "delivery_date": "2099-01-05", "part_of_day": "ochtend",
                "quote": approved_quote,
            })
            self.assertEqual(response.status_code, 409)
            self.assertIn("vraag de klant opnieuw akkoord".encode(), response.data)
        self.db.commit()
        self.assertEqual(self.rows(
            "SELECT COUNT(*) AS n FROM Bestelling"
        )[0]["n"], 0)

    def test_urgent_order_cannot_be_placed_for_tomorrow_and_has_picking_status(self):
        with self.app.test_client() as client:
            preview = client.get("/orders/new?customer_id=4&product_id=1&quantity=1")
            self.assertEqual(preview.status_code, 200)
            approved_quote = re.search(
                rb'name="quote" value="([^"]+)"', preview.data
            ).group(1).decode("ascii")
            from datetime import timedelta
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            invalid = client.post("/orders/new", data={
                "customer_id": "4", "product_id": "1", "quantity": "1",
                "delivery_date": tomorrow, "part_of_day": "middag",
                "urgent": "1", "quote": approved_quote,
            })
            self.assertEqual(invalid.status_code, 400)
            self.assertIn("binnen drie uur".encode(), invalid.data)
            valid = client.post("/orders/new", data={
                "customer_id": "4", "product_id": "1", "quantity": "1",
                "delivery_date": tomorrow, "part_of_day": "middag",
                "quote": approved_quote,
            })
            self.assertEqual(valid.status_code, 302, valid.data[:400])
        self.db.commit()
        self.assertEqual(self.rows("""
            SELECT status_naam AS status FROM Bestelling WHERE klant_id=4
        """)[0]["status"], "wordt verzameld")

    def test_missing_existing_rate_is_not_silently_recalculated(self):
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Bestelling
                    (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                     gewenste_leverdatum, dagdeel)
                VALUES (4, 1, 1, '2025-05-01 09:00:00', '2025-05-02', 'ochtend')
            """)
            cursor.execute("DELETE FROM Klantkorting WHERE klant_id=4")
        self.db.commit()
        with self.assertRaisesRegex(DomainError, "niet vastgelegd"):
            self.service.calculate_total_amount(4, [(1, 1)], date(2026, 11, 1))
        self.assertIsNone(self.discount_repo.get_customer_discount_percentage(4, 2026))

    def test_incomplete_paid_invoice_does_not_partially_write_next_year(self):
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Factuur (klant_id, factuurdatum, betaald_op, totaal_bedrag)
                VALUES (4, '2025-11-01', '2025-11-10', NULL)
            """)
        self.db.commit()
        with self.assertRaises(DomainError):
            self.service.update_annual_discounts(date(2025, 12, 31))
        self.assertEqual(self.rows("SELECT klant_id FROM Klantkorting"), [])


if __name__ == "__main__":
    unittest.main()
