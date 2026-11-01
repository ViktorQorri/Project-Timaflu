"""PR #99 annual-discount and first-order integration against disposable MySQL only.

Requires explicit TIMAFLU_TEST_ALLOW_RESET=isolated and loopback MySQL test settings.
No existing database or production records are modified.
"""
from datetime import date, timedelta
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
            cursor.execute("INSERT INTO Robot (robot_id, gang) VALUES (1, 'A')")
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

    def order_quote(self, client, customer_id, quantity=1, urgent=False, day=None):
        day = day or (date.today() if urgent else date.today() + timedelta(days=1))
        data = {
            "customer_id": str(customer_id),
            "day": day.isoformat(),
            "slot": "middag",
            "product_id": ["1", "", "", "", "", ""],
            "quantity": [str(quantity), "", "", "", "", ""],
            "shortage": ["skip"] * 6,
        }
        if urgent:
            data["urgent"] = "yes"
        return client.post("/orders/quote", data=data)

    def confirm_quote(self, client, preview):
        self.assertEqual(preview.status_code, 200, preview.data[:600])
        match = re.search(rb'name="quote_token" value="([^"]+)"', preview.data)
        self.assertIsNotNone(match)
        return client.post("/orders/confirm", data={
            "quote_token": match.group(1).decode("ascii"),
            "customer_approved": "yes",
        })

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
            preview = self.order_quote(client, 2, quantity=10)
            self.assertIn(b"Klantenkorting", preview.data)
            order = self.confirm_quote(client, preview)
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
            preview = self.order_quote(client, new_customer)
            response = self.confirm_quote(client, preview)
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
            preview = self.order_quote(client, 1, quantity=10)
            self.assertEqual(preview.status_code, 200)

            with self.db.cursor() as cursor:
                cursor.execute("""
                    UPDATE Magazijnlocatie SET aantal = 99
                    WHERE gang = 'A' AND schapnummer = 1
                """)
            self.db.commit()
            response = self.confirm_quote(client, preview)
            self.assertEqual(response.status_code, 409)
            self.assertIn("bespreek de nieuwe prijs opnieuw".encode(), response.data)
        self.db.commit()
        self.assertEqual(self.rows(
            "SELECT COUNT(*) AS n FROM Bestelling"
        )[0]["n"], 0)

    def test_urgent_order_cannot_be_placed_for_tomorrow_and_has_picking_status(self):
        with self.app.test_client() as client:
            tomorrow = date.today() + timedelta(days=1)
            invalid = self.order_quote(client, 4, urgent=True, day=tomorrow)
            self.assertEqual(invalid.status_code, 400)
            self.assertIn("binnen maximaal drie uur".encode(), invalid.data)
            valid_preview = self.order_quote(client, 4, day=tomorrow)
            valid = self.confirm_quote(client, valid_preview)
            self.assertEqual(valid.status_code, 302, valid.data[:400])
        self.db.commit()
        self.assertEqual(self.rows("""
            SELECT status_naam AS status FROM Bestelling WHERE klant_id=4
        """)[0]["status"], "wordt verzameld")

    def test_address_changed_after_approval_requires_a_new_quote(self):
        with self.db.cursor() as cursor:
            cursor.execute("""
                INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)
                VALUES (1, %s, 5.00)
            """, (date.today().year,))
        self.db.commit()
        with self.app.test_client() as client:
            preview = self.order_quote(client, 1, quantity=2)
            self.assertEqual(preview.status_code, 200)
            self.assertIn(b"Afleveradres:", preview.data)
            self.assertIn(b"Factuuradres:", preview.data)
            self.assertIn(b"Fictieve teststraat 1", preview.data)
            with self.db.cursor() as cursor:
                cursor.execute(
                    "UPDATE Adres SET adres='Aangepast testadres 2' WHERE adres_id=1"
                )
            self.db.commit()
            response = self.confirm_quote(client, preview)
            self.assertEqual(response.status_code, 409)
        self.db.commit()
        self.assertEqual(self.rows(
            "SELECT COUNT(*) AS n FROM Bestelling"
        )[0]["n"], 0)

    def test_order_form_can_add_more_than_twelve_lines_without_losing_values(self):
        with self.app.test_client() as client:
            qs = [
                ("customer_id", "1"), ("day", "2099-01-05"),
                ("slot", "ochtend"), ("add_line", "1"),
            ]
            for index in range(13):
                qs.extend((
                    ("product_id", "1" if index == 0 else ""),
                    ("quantity", "2" if index == 0 else ""),
                    ("shortage", "skip"),
                ))
            response = client.get("/orders/new", query_string=qs)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b'medicine-13', response.data)
            self.assertIn(b'value="2"', response.data)
            self.assertIn(b'name="customer_id"', response.data)

    def test_rush_delivery_plan_enforces_three_hour_deadline(self):
        from datetime import datetime, time
        from repositories.distribution_preparation_repository import (
            DistributionPreparationRepository,
        )

        day = date.today()
        with self.db.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Koerier (naam, beschikbaar) VALUES ('Spoedkoerier test', TRUE)"
            )
            courier = cursor.lastrowid
            cursor.execute(
                """INSERT INTO Bestelling
                   (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                    gewenste_leverdatum, dagdeel, spoed, status_naam)
                   VALUES (1, 1, 1, %s, %s, 'ochtend', TRUE, 'wordt verzameld')""",
                (datetime.combine(day, time(8, 0)), day),
            )
            order_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Levering (bestelling_id) VALUES (%s)", (order_id,)
            )
            delivery_id = cursor.lastrowid
        self.db.commit()

        repository = DistributionPreparationRepository(self.db)
        for invalid_time in (time(7, 59), time(11, 1)):
            with self.subTest(invalid_time=invalid_time):
                with self.assertRaisesRegex(DomainError, "uiterlijk drie uur"):
                    repository.schedule(delivery_id, courier, day, invalid_time)
                self.assertEqual(
                    self.rows("SELECT COUNT(*) AS n FROM Leverpoging")[0]["n"], 0
                )
        repository.schedule(delivery_id, courier, day, time(10, 0))
        self.assertEqual(
            self.rows("SELECT COUNT(*) AS n FROM Leverpoging")[0]["n"], 1
        )
        self.assertEqual(
            self.rows(
                "SELECT status_naam FROM Bestelling WHERE bestelling_id=%s",
                (order_id,),
            )[0]["status_naam"], "verstuurd"
        )

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
