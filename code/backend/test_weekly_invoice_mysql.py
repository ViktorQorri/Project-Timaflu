"""Real MySQL 8.4 + Flask end-to-end evidence for weekly invoice issuing.

Run only against an isolated Docker database on localhost:
  TIMAFLU_TEST_MYSQL_PORT=33078
  TIMAFLU_TEST_MYSQL_PASSWORD=...  (temporary test password)
  TIMAFLU_TEST_ALLOW_RESET=isolated
  python -m unittest test_weekly_invoice_mysql -v
All tests skip automatically without explicit isolation opt-in.
"""
from datetime import date
from decimal import Decimal
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import mysql.connector

from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.weekly_invoice_repository import WeeklyInvoiceRepository

ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "timaflu_casus_test_94"
TEST_ADDRESS = "TESTGEGEVENS: Fictieve Afzenderstraat 9, Breda"


@unittest.skipUnless(
    os.getenv("TIMAFLU_TEST_ALLOW_RESET") == "isolated"
    and os.getenv("TIMAFLU_TEST_MYSQL_HOST") == "127.0.0.1",
    "Only runs with explicitly isolated localhost MySQL",
)
class WeeklyInvoiceMySqlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db_opts = dict(
            host="127.0.0.1",
            port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
            user=os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
            password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        )

    def setUp(self):
        admin = mysql.connector.connect(**self.db_opts)
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"DROP DATABASE IF EXISTS {DB_NAME}")
                cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4")
            admin.commit()
        finally:
            admin.close()

        self.db = mysql.connector.connect(**self.db_opts, database=DB_NAME)
        for filename in (
            ROOT / "code/database/schema.sql",
            ROOT / "Documentation/Architecture/test-data/weekly_invoicing_fixture.sql"
        ):
            script = "\n".join(line for line in filename.read_text(encoding="utf-8").splitlines()
                               if not line.lstrip().startswith("--"))
            with self.db.cursor() as cursor:
                for statement in script.split(";"):
                    if statement.strip():
                        cursor.execute(statement)
        self.db.commit()
        self.app = create_app()
        self.app.config.update(
            TESTING=True, SECRET_KEY="test-key", DB_HOST="127.0.0.1",
            DB_PORT=self.db_opts["port"], DB_NAME=DB_NAME,
            DB_USER=self.db_opts["user"], DB_PASSWORD=self.db_opts["password"],
            TIMAFLU_ADDRESS=TEST_ADDRESS
        )

    def tearDown(self):
        self.db.close()

    def fetchone(self, query, params=()):
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def test_http_weekly_invoice_is_atomic_and_idempotent(self):
        week = date(2026,10,19)
        with self.app.test_client() as client:
            page=client.get("/invoices/weekly?week_start=2026-10-19")
            self.assertEqual(page.status_code, 200, page.data[:400])
            self.assertIn(b"TESTGEGEVENS",page.data)
            response=client.post("/invoices/weekly", data={"week_start":"2026-10-19"})
            self.assertEqual(response.status_code,302,response.data[:300])
            invoice_id = self.fetchone(
                "SELECT factuur_id FROM Factuur WHERE week_start=%s", (week,)
            )["factuur_id"]
            invoice=self.fetchone("SELECT * FROM Factuur WHERE factuur_id=%s",(invoice_id,))
            self.assertEqual(invoice["bedrag_excl_btw"],Decimal("700.00"))
            self.assertEqual(invoice["btw_bedrag"],Decimal("63.00"))
            self.assertEqual(invoice["bedrag_incl_btw"],Decimal("763.00"))
            self.assertEqual(invoice["bestellingskorting"],Decimal("32.70"))
            self.assertEqual(invoice["eenmalige_korting"],Decimal("62.13"))
            self.assertEqual(invoice["klantenkorting"],Decimal("33.41"))
            self.assertEqual(invoice["totaal_bedrag"],Decimal("634.76"))
            self.assertEqual(invoice["afzenderadres"],TEST_ADDRESS)
            self.assertEqual(invoice["factuuradres"],"TEST: Factuurstraat 12, Breda")
            page=client.get(f"/invoices/issued/{invoice_id}")
            self.assertEqual(page.status_code,200,page.data[:600])
            self.assertIn(b"634.76",page.data)
            self.assertIn(b"TESTGEGEVENS",page.data)
            self.assertIn(b"TEST: Factuurstraat 12",page.data)

            again=client.post("/invoices/weekly",data={"week_start":"2026-10-19"})
            self.assertEqual(again.status_code,302)
        self.assertEqual(
            self.fetchone("SELECT COUNT(*) AS n FROM Factuur WHERE week_start=%s",(week,))["n"],1
        )
        self.assertEqual(
            self.fetchone("SELECT COUNT(*) AS n FROM Leveringregel WHERE factuur_id IS NOT NULL")["n"],2
        )
        self.assertIsNone(
            self.fetchone("SELECT factuur_id FROM Leveringregel WHERE levering_id=3")["factuur_id"]
        )
        self.assertEqual(
            self.fetchone("SELECT eenmalige_korting_toegepast AS used FROM Bestelling WHERE bestelling_id=1")["used"],1
        )
        self.assertEqual(
            self.fetchone("SELECT eenmalige_korting_toegepast AS used FROM Bestelling WHERE bestelling_id=2")["used"],0
        )
        # Persisted sender and customer address must not change with the account.
        with self.db.cursor() as c:
            c.execute("UPDATE Adres SET adres='Gewijzigd later' WHERE adres_id=1")
        self.db.commit()
        with self.app.test_client() as client:
            page=client.get(f"/invoices/issued/{invoice_id}")
            self.assertIn(b"TEST: Factuurstraat 12, Breda",page.data)
            self.assertNotIn(b"Gewijzigd later",page.data)

    def test_next_week_never_reuses_first_order_discount(self):
        repo=WeeklyInvoiceRepository(self.db)
        first=repo.issue_week(date(2026,10,19),TEST_ADDRESS,date(2026,10,31))
        self.assertEqual(len(first),1)
        second=repo.issue_week(date(2026,10,26),TEST_ADDRESS,date(2026,11,3))
        self.assertEqual(len(second),1)
        next_invoice=self.fetchone("SELECT * FROM Factuur WHERE factuur_id=%s",(second[0],))
        self.assertEqual(next_invoice["eenmalige_korting"],Decimal("0.00"))
        self.assertEqual(next_invoice["totaal_bedrag"],Decimal("103.55"))
        self.assertEqual(repo.issue_week(date(2026,10,19),TEST_ADDRESS,date(2026,11,3)),[])
        self.assertEqual(repo.issue_week(date(2026,10,26),TEST_ADDRESS,date(2026,11,3)),[])

    def test_partial_first_order_keeps_its_discount_in_later_week(self):
        # De korting hoort bij de eerste BESTELLING, niet alleen bij haar eerste levering.
        with self.db.cursor() as c:
            c.execute("UPDATE Bestelregel SET aantal=7 WHERE bestelling_id=1 AND product_id=1")
            c.execute("INSERT INTO Levering(bestelling_id) VALUES (1)")
            later = c.lastrowid
            c.execute("INSERT INTO Leveringregel(levering_id,product_id,aantal_geleverd) VALUES (%s,1,1)", (later,))
            c.execute(
                "INSERT INTO Leverpoging(levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend) "
                "VALUES(%s,1,2,'13:00:00','afgeleverd',TRUE)", (later,)
            )
        self.db.commit()
        repo=WeeklyInvoiceRepository(self.db)
        repo.issue_week(date(2026,10,19),TEST_ADDRESS,date(2026,10,31))
        second=repo.issue_week(date(2026,10,26),TEST_ADDRESS,date(2026,11,3))
        self.assertEqual(len(second),1)
        invoice=self.fetchone("SELECT * FROM Factuur WHERE factuur_id=%s",(second[0],))
        self.assertEqual(invoice["eenmalige_korting"],Decimal("10.36"))
        self.assertEqual(invoice["bestellingskorting"],Decimal("5.45"))
        self.assertEqual(invoice["totaal_bedrag"],Decimal("192.08"))
        self.assertEqual(repo.issue_week(date(2026,10,26),TEST_ADDRESS,date(2026,11,3)),[])

    def test_500_euro_order_discount_survives_partial_delivery_below_threshold(self):
        # Bij 2 van 6 stuks is de eerste levering kleiner dan 500, de bestelling niet.
        with self.db.cursor() as c:
            c.execute("UPDATE Leveringregel SET aantal_geleverd=2 WHERE levering_id=1 AND product_id=1")
        self.db.commit()
        ids=WeeklyInvoiceRepository(self.db).issue_week(
            date(2026,10,19),TEST_ADDRESS,date(2026,10,31)
        )
        invoice=self.fetchone("SELECT * FROM Factuur WHERE factuur_id=%s",(ids[0],))
        self.assertEqual(invoice["bestellingskorting"],Decimal("10.90"))

    def test_reminder_spacing_duplicate_prevention_and_paid_invoice_safety(self):
        repo=WeeklyInvoiceRepository(self.db)
        ids=repo.issue_week(date(2026,10,19),TEST_ADDRESS,date(2026,10,31))
        self.assertEqual(len(ids),1)
        invoice_id=ids[0]
        actions=AssessedRepository(self.db)
        actions.record_payment_action(invoice_id,"reminder1",date(2026,11,8))
        with self.assertRaises(DomainError):
            actions.record_payment_action(invoice_id,"reminder1",date(2026,11,9))
        with self.assertRaises(DomainError):
            actions.record_payment_action(invoice_id,"reminder2",date(2026,11,14))
        actions.record_payment_action(invoice_id,"reminder2",date(2026,11,15))
        with self.assertRaises(DomainError):
            actions.record_payment_action(invoice_id,"reminder2",date(2026,11,16))
        row=self.fetchone(
            "SELECT COUNT(*) AS n FROM Betalingsherinnering WHERE factuur_id=%s",
            (invoice_id,))
        self.assertEqual(row["n"],2)

    def test_real_customer_lookup_and_order_status_from_mysql(self):
        with self.app.test_client() as client:
            customers=client.get("/customers?q=TEST")
            self.assertEqual(customers.status_code,200)
            self.assertIn(b"TEST Apotheek",customers.data)
            self.assertIn(b"TEST: Factuurstraat 12, Breda",customers.data)
            statuses=client.get("/orders/status?customer_id=1")
            self.assertEqual(statuses.status_code,200)
            self.assertIn(b"Orderstatus controleren",statuses.data)
            self.assertIn(b"afgeleverd",statuses.data)
            self.assertIn(b"verstuurd",statuses.data)
            self.assertEqual(client.get("/orders/status?customer_id=wrong").status_code,400)
        self.assertEqual(self.fetchone("SELECT COUNT(*) AS n FROM Bestelling")["n"],4)

    def test_missing_sender_address_and_incomplete_week_block_issuance(self):
        with self.app.test_client() as client:
            self.app.config["TIMAFLU_ADDRESS"]=""
            response=client.post("/invoices/weekly",data={"week_start":"2026-10-19"})
            self.assertEqual(response.status_code,400)
            self.assertIn("werkelijke Timaflu-afzenderadres".encode(),response.data)
        self.assertEqual(self.fetchone("SELECT COUNT(*) AS n FROM Factuur")["n"],0)
        with self.assertRaises(DomainError):
            WeeklyInvoiceRepository(self.db).issue_week(
                date(2026,10,26),TEST_ADDRESS,date(2026,10,31)
            )

    def test_failed_snapshot_rolls_back_invoice_and_line_links(self):
        repo=WeeklyInvoiceRepository(self.db)
        with patch.object(AssessedRepository,"save_invoice_snapshot",
                          side_effect=RuntimeError("simulated save failure")):
            with self.assertRaises(RuntimeError):
                repo.issue_week(date(2026,10,19),TEST_ADDRESS,date(2026,10,31))
        self.assertEqual(self.fetchone("SELECT COUNT(*) AS n FROM Factuur")["n"],0)
        self.assertEqual(
            self.fetchone("SELECT COUNT(*) AS n FROM Leveringregel WHERE factuur_id IS NOT NULL")["n"],0
        )
        self.assertEqual(
            self.fetchone("SELECT eenmalige_korting_toegepast AS used FROM Bestelling WHERE bestelling_id=1")["used"],0
        )

    def test_existing_database_migration_adds_unique_week_and_snapshot_addresses(self):
        # Simulate the previous schema, then apply the shipped one-time migration.
        with self.db.cursor() as cursor:
            # Preserve the customer FK index while removing the new unique key.
            cursor.execute("ALTER TABLE Factuur ADD INDEX idx_legacy_klant_id (klant_id)")
            cursor.execute("""
                ALTER TABLE Factuur DROP INDEX uq_factuur_klant_week,
                DROP COLUMN week_start, DROP COLUMN afzenderadres,
                DROP COLUMN factuuradres
            """)
        script = (ROOT/"code/database/migrations/2026_10_31_weekly_issuance.sql"
                  ).read_text(encoding="utf-8")
        script = "\n".join(line for line in script.splitlines()
                           if not line.lstrip().startswith("--"))
        with self.db.cursor() as cursor:
            for statement in script.split(";"):
                if statement.strip():
                    cursor.execute(statement)
            cursor.execute("""
                SELECT COLUMN_NAME FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='Factuur'
                  AND COLUMN_NAME IN ('week_start','afzenderadres','factuuradres')
            """, (DB_NAME,))
            self.assertEqual({row[0] for row in cursor.fetchall()},
                             {"week_start","afzenderadres","factuuradres"})
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA=%s AND TABLE_NAME='Factuur'
                  AND INDEX_NAME='uq_factuur_klant_week'
            """, (DB_NAME,))
            self.assertEqual(cursor.fetchone()[0],2)

    def test_paid_invoice_keeps_snapshot_and_viewable_detail(self):
        ids=WeeklyInvoiceRepository(self.db).issue_week(
            date(2026,10,19),TEST_ADDRESS,date(2026,10,31))
        with self.db.cursor() as cursor:
            cursor.execute("UPDATE Factuur SET betaald_op='2026-11-05' WHERE factuur_id=%s",(ids[0],))
        self.db.commit()
        with self.app.test_client() as client:
            self.assertEqual(client.get(f"/invoices/issued/{ids[0]}").status_code,200)
            unpaid=client.get("/invoices?customer_id=1")
            self.assertNotIn(b"Factuur 1</a>",unpaid.data)


if __name__ == "__main__":
    unittest.main()
