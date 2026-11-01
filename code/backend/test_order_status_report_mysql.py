"""MySQL 8.4 integration tests for the read-only PR95 status overview.

These tests use only a uniquely named disposable schema on local MySQL.
The customer-facing AD06 search/detail/backorder flow belongs to PR97.
"""
import os
import unittest
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import mysql.connector

from app import create_app
from repositories.order_status_report_repository import OrderStatusReportRepository

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    os.getenv("TIMAFLU_TEST_ALLOW_RESET") == "isolated"
    and os.getenv("TIMAFLU_TEST_MYSQL_HOST") == "127.0.0.1",
    "Requires an explicitly isolated local MySQL instance",
)
class OrderStatusReportMySQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database_name = "pr95_status_" + uuid4().hex[:12]
        cls.options = {
            "host": "127.0.0.1",
            "port": int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
            "user": "root",
            "password": os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
            "connection_timeout": 10,
        }
        admin = mysql.connector.connect(**cls.options)
        try:
            with admin.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE {cls.database_name} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            admin.commit()
        finally:
            admin.close()
        try:
            cls.connection = mysql.connector.connect(
                **cls.options, database=cls.database_name
            )
            schema = (ROOT / "code/database/schema.sql").read_text(encoding="utf-8-sig")
            without_comments = "\n".join(
                line for line in schema.splitlines()
                if not line.lstrip().startswith("--")
            )
            with cls.connection.cursor() as cur:
                for statement in without_comments.split(";"):
                    if statement.strip():
                        cur.execute(statement.strip())
            cls.connection.commit()
            cls._seed()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def _seed(cls):
        with cls.connection.cursor() as cur:
            cur.execute("INSERT INTO Adres (adres) VALUES ('Casusstraat 1, Breda')")
            address_id = cur.lastrowid
            cur.execute(
                """INSERT INTO Klant
                   (bedrijfsnaam, afleveradres_id, betaaladres_id)
                   VALUES ('Apotheek casus', %s, %s)""",
                (address_id, address_id),
            )
            customer_id = cur.lastrowid
            cls.saved_statuses = [
                "wordt verzameld", "verstuurd", "backorder",
                "afgeleverd", "niet afgeleverd",
            ]
            cls.order_ids = []
            for i, status in enumerate(cls.saved_statuses, 1):
                cur.execute(
                    """INSERT INTO Bestelling (
                       klant_id, afleveradres_id, betaaladres_id,
                       besteld_op, gewenste_leverdatum, dagdeel, spoed, status_naam
                       ) VALUES (%s, %s, %s, %s, '2026-11-12', 'middag', %s, %s)""",
                    (customer_id, address_id, address_id,
                     datetime(2026, 11, 1, 10, i), i % 2 == 0, status),
                )
                cls.order_ids.append(cur.lastrowid)
            # The original case preserves historical orders after changes to customers.
            cur.execute(
                "UPDATE Klant SET actief = FALSE WHERE klant_id = %s",
                (customer_id,),
            )
        cls.connection.commit()

    @classmethod
    def tearDownClass(cls):
        connection = getattr(cls, "connection", None)
        if connection is not None:
            connection.close()
        if not getattr(cls, "database_name", None):
            return
        admin = mysql.connector.connect(**cls.options)
        try:
            with admin.cursor() as cur:
                cur.execute(f"DROP DATABASE IF EXISTS {cls.database_name}")
            admin.commit()
        finally:
            admin.close()

    def test_all_valid_recorded_statuses_are_displayed_without_reclassification(self):
        rows = OrderStatusReportRepository(self.connection).list_orders()
        self.assertEqual(len(rows), len(self.saved_statuses))
        self.assertEqual(
            [row["bestelling_id"] for row in rows], list(reversed(self.order_ids))
        )
        self.assertEqual(
            [row["status_naam"] for row in rows], list(reversed(self.saved_statuses))
        )
        self.assertEqual(
            {row["bedrijfsnaam"] for row in rows}, {"Apotheek casus"}
        )

    def test_live_status_page_shows_backorder_and_delivery_without_extra_rules(self):
        app = create_app()
        app.config.update(
            TESTING=True, DB_HOST="127.0.0.1",
            DB_PORT=self.options["port"], DB_NAME=self.database_name,
            DB_USER="root", DB_PASSWORD=self.options["password"],
        )
        with app.test_client() as client:
            response = client.get("/reports")
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            for label in (
                "Wordt verzameld", "Verstuurd", "Backorder", "Afgeleverd",
                "Niet afgeleverd",
                "Apotheek casus", "12-11-2026", "middag", "Spoed",
            ):
                self.assertIn(label, html)
            self.assertEqual(html.count("<tr>"), len(self.saved_statuses) + 1)
            self.assertNotIn("Openstaande orders", html)
            self.assertNotIn('name="order"', html)
            self.assertNotIn('name="from"', html)
            self.assertNotIn('name="to"', html)
            self.assertNotIn('href="/reports/', html)

    def test_report_only_reads_existing_orders_and_does_not_mutate_them(self):
        repo = OrderStatusReportRepository(self.connection)
        with self.connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM Bestelling")
            count_before = cur.fetchone()[0]
        for _ in range(2):
            self.assertEqual(len(repo.list_orders()), count_before)
        with self.connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM Bestelling")
            self.assertEqual(cur.fetchone()[0], count_before)
