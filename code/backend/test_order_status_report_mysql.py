"""Opt-in actual MySQL 8.4 checks for PR95/AD06.

Only enabled for an explicitly isolated local database. Creates and removes
a uniquely named test schema; never connects to remote or production MySQL.
"""

import os
import unittest
from pathlib import Path
from uuid import uuid4

import mysql.connector

from app import create_app
from repositories.order_status_report_repository import OrderStatusReportRepository

ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    os.getenv("TIMAFLU_TEST_ALLOW_RESET") == "isolated"
    and os.getenv("TIMAFLU_TEST_MYSQL_HOST") == "127.0.0.1",
    "Requires explicitly isolated MySQL bound to 127.0.0.1",
)
class OrderStatusReportMySQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_name = "pr95_ad06_" + uuid4().hex[:12]
        cls.connection_options = dict(
            host="127.0.0.1",
            port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
            user="root",
            password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
            connection_timeout=10,
        )
        admin = mysql.connector.connect(**cls.connection_options)
        try:
            with admin.cursor() as cursor:
                cursor.execute(
                    f"CREATE DATABASE {cls.db_name} "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            admin.commit()
        finally:
            admin.close()
        cls.connection_options["database"] = cls.db_name
        cls.connection = mysql.connector.connect(**cls.connection_options)
        try:
            cls._load_schema()
            cls._seed_orders()
        except Exception:
            cls.tearDownClass()
            raise

    @classmethod
    def _load_schema(cls):
        schema = (ROOT / "code/database/schema.sql").read_text(encoding="utf-8-sig")
        statements = "\n".join(
            line for line in schema.splitlines() if not line.lstrip().startswith("--")
        )
        with cls.connection.cursor() as cursor:
            for statement in statements.split(";"):
                if statement.strip():
                    cursor.execute(statement)
        cls.connection.commit()

    @classmethod
    def _seed_orders(cls):
        with cls.connection.cursor() as cursor:
            cursor.execute("INSERT INTO Adres(adres) VALUES('Casusstraat 1, Breda')")
            address = cursor.lastrowid
            for name in ("Apotheek Alfa_%", "Apotheek Beta"):
                cursor.execute(
                    "INSERT INTO Klant(bedrijfsnaam,afleveradres_id,betaaladres_id) "
                    "VALUES(%s,%s,%s)", (name, address, address)
                )
            cursor.execute("SELECT klant_id, bedrijfsnaam FROM Klant ORDER BY klant_id")
            customers = {name: ident for ident, name in cursor.fetchall()}
            cls.alpha_id = customers["Apotheek Alfa_%"]
            cls.beta_id = customers["Apotheek Beta"]
            for i in range(1, 3):
                cursor.execute(
                    """INSERT INTO Product
                       (artikelnummer,bestelcode,productnaam,prijs_per_grootverpakking,
                        aantal_detailverpakkingen,minimale_bestelhoeveelheid,minimumvoorraad)
                       VALUES(%s,%s,%s,15.50,1,1,0)""",
                    (f"TEST-{i}", f"CODE-{i}", f"Testmedicijn {i}")
                )
            for client, status, index in (
                (cls.alpha_id, "backorder", 1),
                (cls.beta_id, "afgeleverd", 2),
                (cls.alpha_id, None, 3),
            ):
                cursor.execute(
                    """INSERT INTO Bestelling
                       (klant_id,afleveradres_id,betaaladres_id,besteld_op,
                        gewenste_leverdatum,dagdeel,spoed,status_naam)
                       VALUES(%s,%s,%s,%s,'2026-11-10','middag',FALSE,%s)""",
                    (client, address, address, f"2026-11-01 10:0{index}:00", status)
                )
                setattr(cls, f"order{index}", cursor.lastrowid)
            for order, product, amount, choice in (
                (cls.order1, 1, 5, True),
                (cls.order1, 2, 2, None),
                (cls.order2, 1, 1, False),
            ):
                cursor.execute(
                    """INSERT INTO Bestelregel
                       (bestelling_id,product_id,aantal,prijs_per_eenheid,afnemen_bij_tekort)
                       VALUES(%s,%s,%s,12.50,%s)""",
                    (order, product, amount, choice)
                )
            # Historical orders remain visible after customer deactivation.
            cursor.execute(
                "UPDATE Klant SET actief=FALSE WHERE klant_id=%s", (cls.beta_id,)
            )
        cls.connection.commit()

    @classmethod
    def tearDownClass(cls):
        connection = getattr(cls, "connection", None)
        if connection is not None:
            connection.close()
        options = dict(cls.connection_options)
        options.pop("database", None)
        admin = mysql.connector.connect(**options)
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {cls.db_name}")
            admin.commit()
        finally:
            admin.close()

    def test_actual_search_by_number_and_literal_customer_name(self):
        repo = OrderStatusReportRepository(self.connection)
        self.assertEqual(
            [row["bestelling_id"] for row in repo.search_orders(str(self.order1))],
            [self.order1]
        )
        self.assertEqual(
            {row["bestelling_id"] for row in repo.search_orders("Alfa_%")},
            {self.order1, self.order3}
        )
        self.assertEqual(repo.search_orders("Alfa_% is geen klant"), [])
        self.assertEqual(repo.search_orders("bestaat niet"), [])
        self.assertEqual(repo.search_orders("' OR 1=1 --"), [])

    def test_detail_returns_order_lines_and_true_shortage_choices(self):
        repo = OrderStatusReportRepository(self.connection)
        order = repo.find_order(self.order1)
        self.assertEqual(order["status_naam"], "backorder")
        self.assertEqual(order["dagdeel"], "middag")
        lines = repo.list_order_lines(self.order1)
        self.assertEqual(len(lines), 2)
        self.assertEqual({row["aantal"] for row in lines}, {2, 5})
        self.assertIn(None, [row["afnemen_bij_tekort"] for row in lines])
        self.assertIn(1, [row["afnemen_bij_tekort"] for row in lines])
        self.assertEqual(repo.list_order_lines(self.order3), [])

    def test_full_browser_routes_and_missing_order(self):
        app = create_app()
        app.config.update(
            TESTING=True, DB_HOST="127.0.0.1",
            DB_PORT=self.connection_options["port"], DB_NAME=self.db_name,
            DB_USER="root", DB_PASSWORD=self.connection_options["password"],
        )
        with app.test_client() as client:
            for url in (
                "/reports",
                "/reports?order=Alfa_%25",
                f"/reports?order={self.order1}",
                f"/reports/{self.order1}",
                f"/reports/{self.order2}",
                f"/reports/{self.order3}",
            ):
                response = client.get(url)
                self.assertEqual(response.status_code, 200, url)
            first = client.get(f"/reports/{self.order1}").get_data(as_text=True)
            self.assertIn("Backorderinformatie", first)
            self.assertIn("Geaccepteerd", first)
            self.assertIn("Niet vastgelegd", first)
            self.assertIn("Testmedicijn 1", first)
            self.assertIn("10-11-2026", first)
            last = client.get(f"/reports/{self.order3}").get_data(as_text=True)
            self.assertIn("Geen bestelregels geregistreerd.", last)
            missing = client.get("/reports/999999")
            self.assertEqual(missing.status_code, 404)
            self.assertIn("Geen order gevonden.", missing.get_data(as_text=True))
            empty = client.get("/reports?order=Onvindbaar")
            self.assertIn("Geen order gevonden.", empty.get_data(as_text=True))

    def test_no_history_deleted_and_read_only_queries(self):
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Bestelling")
            before = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Bestelregel")
            lines_before = cursor.fetchone()[0]
        repo = OrderStatusReportRepository(self.connection)
        self.assertEqual(len(repo.list_orders()), 3)
        self.assertIsNotNone(repo.find_order(self.order2))
        repo.list_order_lines(self.order1)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Bestelling")
            self.assertEqual(cursor.fetchone()[0], before)
            cursor.execute("SELECT COUNT(*) FROM Bestelregel")
            self.assertEqual(cursor.fetchone()[0], lines_before)
