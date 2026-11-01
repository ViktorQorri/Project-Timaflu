"""MySQL 8.4 integration: actual invoice reminders, no invented customer email address."""
from datetime import date, timedelta
from decimal import Decimal
import os
from pathlib import Path
import unittest
from uuid import uuid4

import mysql.connector

from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


ROOT = Path(__file__).resolve().parents[2]


@unittest.skipUnless(
    os.getenv("TIMAFLU_TEST_ALLOW_RESET") == "isolated"
    and os.getenv("TIMAFLU_TEST_MYSQL_HOST") == "127.0.0.1",
    "Runs only with explicitly isolated localhost MySQL",
)
class PaymentReminderMySqlTests(unittest.TestCase):
    def setUp(self):
        self.opts = dict(
            host="127.0.0.1", port=int(os.environ["TIMAFLU_TEST_MYSQL_PORT"]),
            user=os.getenv("TIMAFLU_TEST_MYSQL_USER", "root"),
            password=os.environ["TIMAFLU_TEST_MYSQL_PASSWORD"],
        )
        self.name = "timaflu_issue22_" + uuid4().hex[:12]
        admin = mysql.connector.connect(**self.opts)
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE {self.name} CHARACTER SET utf8mb4")
            admin.commit()
        finally:
            admin.close()
        self.db = mysql.connector.connect(**self.opts, database=self.name)
        schema = ROOT / "code/database/schema.sql"
        contents = "\n".join(
            line for line in schema.read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("--")
        )
        with self.db.cursor() as cursor:
            for statement in contents.split(";"):
                if statement.strip():
                    cursor.execute(statement)
            cursor.execute(
                "INSERT INTO Adres(adres) VALUES (%s), (%s)",
                ("TEST: Oud factuuradres, Breda", "TEST: Huidig factuuradres, Breda"),
            )
            cursor.execute(
                """INSERT INTO Klant(
                     bedrijfsnaam, contactpersoon, telefoonnummer,
                     afleveradres_id, betaaladres_id
                   ) VALUES ('TEST apotheek', 'TEST medewerker', '0600000000', 2, 2)"""
            )
            today = date.today()
            for days, amount, paid_on in (
                (8, Decimal("125.00"), None),
                (15, Decimal("350.00"), None),
                (8, Decimal("55.00"), today),
                (22, Decimal("400.00"), None),
                (4, Decimal("250.00"), None),
            ):
                cursor.execute(
                    """INSERT INTO Factuur
                       (klant_id, factuurdatum, betaald_op, totaal_bedrag,
                        factuuradres, afzenderadres)
                       VALUES (1, %s, %s, %s, %s, %s)""",
                    (today - timedelta(days=days), paid_on, amount,
                     "TEST: Oud factuuradres, Breda", "TEST: Timaflu afzender"),
                )
            cursor.execute(
                """INSERT INTO Betalingsherinnering
                   (factuur_id, volgnummer, verstuurd_op) VALUES (2, 1, %s)""",
                (today - timedelta(days=8),),
            )
        self.db.commit()
        self.app = create_app()
        self.app.config.update(
            TESTING=True, SECRET_KEY="issue22-tests-only",
            DB_HOST=self.opts["host"], DB_PORT=self.opts["port"],
            DB_USER=self.opts["user"], DB_PASSWORD=self.opts["password"],
            DB_NAME=self.name,
        )

    def tearDown(self):
        self.db.close()
        admin = mysql.connector.connect(**self.opts)
        try:
            with admin.cursor() as cursor:
                cursor.execute(f"DROP DATABASE {self.name}")
            admin.commit()
        finally:
            admin.close()

    def reminder_count(self, invoice_id):
        # Browser requests commit through a different DB connection. Start a
        # new MySQL snapshot rather than reuse the older REPEATABLE READ snapshot.
        self.db.rollback()
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS aantal FROM Betalingsherinnering WHERE factuur_id = %s",
                (invoice_id,),
            )
            return cursor.fetchone()["aantal"]

    def test_unpaid_overview_excludes_paid_and_shows_real_weeks_and_reminders(self):
        with self.app.test_client() as client:
            response = client.get("/invoices/outstanding")
        self.assertEqual(response.status_code, 200)
        content = response.get_data(as_text=True)
        for number in (1, 2, 4, 5):
            self.assertIn(f'<th scope="row">{number}</th>', content)
        self.assertNotIn('<th scope="row">3</th>', content)
        self.assertIn("Eerste herinnering voorbereiden", content)
        self.assertIn("Tweede herinnering voorbereiden", content)
        self.assertIn("Klant bellen en standaard betalingsregeling voorstellen", content)
        self.assertEqual(self.reminder_count(1), 0)

    def test_printed_first_reminder_does_not_send_and_requires_dispatch_confirmation(self):
        with self.app.test_client() as client:
            preview = client.get("/invoices/1/reminders/1")
            self.assertEqual(preview.status_code, 200)
            letter = preview.get_data(as_text=True)
            self.assertIn("TEST: Oud factuuradres, Breda", letter)
            self.assertNotIn("TEST: Huidig factuuradres, Breda", letter)
            self.assertIn("125.00", letter)
            self.assertIn("Timaflu afzender", letter)
            self.assertEqual(self.reminder_count(1), 0)
            denied = client.post("/invoices/1/reminders/1/sent", data={})
            self.assertEqual(denied.status_code, 400)
            self.assertEqual(self.reminder_count(1), 0)
            confirmed = client.post(
                "/invoices/1/reminders/1/sent",
                data={"sent_confirmed": "yes"},
            )
            self.assertEqual(confirmed.status_code, 302)
            self.assertEqual(self.reminder_count(1), 1)
            duplicate = client.post(
                "/invoices/1/reminders/1/sent",
                data={"sent_confirmed": "yes"},
            )
            self.assertEqual(duplicate.status_code, 409)
            self.assertEqual(self.reminder_count(1), 1)

    def test_second_reminder_then_duplicate_rejected_with_real_dates(self):
        with self.app.test_client() as client:
            preview = client.get("/invoices/2/reminders/2")
            self.assertEqual(preview.status_code, 200)
            self.assertIn(b"350.00", preview.data)
            recorded = client.post(
                "/invoices/2/reminders/2/sent",
                data={"sent_confirmed": "yes"},
            )
            self.assertEqual(recorded.status_code, 302)
            self.assertEqual(self.reminder_count(2), 2)
            again = client.post(
                "/invoices/2/reminders/2/sent",
                data={"sent_confirmed": "yes"},
            )
            self.assertEqual(again.status_code, 409)
            self.assertEqual(self.reminder_count(2), 2)

    def test_paid_early_and_unsupported_reminders_are_rejected(self):
        with self.app.test_client() as client:
            self.assertEqual(client.get("/invoices/3/reminders/1").status_code, 400)
            self.assertEqual(client.get("/invoices/5/reminders/1").status_code, 400)
            self.assertEqual(client.get("/invoices/1/reminders/2").status_code, 400)
            self.assertEqual(client.get("/invoices/99/reminders/1").status_code, 404)
            self.assertEqual(client.get("/invoices/1/reminders/3").status_code, 400)
        self.assertEqual(self.reminder_count(1), 0)

    def test_due_customer_contact_and_collection_block_remain_existing_case_processes(self):
        records = AssessedRepository(self.db).unpaid_invoice_overview(date.today())
        overdue = next(row for row in records if row["factuur_id"] == 4)
        self.assertEqual(overdue["weken_open"], 3)
        self.assertEqual(overdue["vervolgactie"], "contact")
        AssessedRepository(self.db).record_payment_action(
            4, "payment_plan_rejected", date.today()
        )
        new = AssessedRepository(self.db).unpaid_invoice_overview(date.today())
        self.assertEqual(
            next(row for row in new if row["factuur_id"] == 4)["vervolgactie"],
            "incasso",
        )
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute(
                "SELECT incasso_ingeschakeld FROM Factuur WHERE factuur_id = 4"
            )
            self.assertEqual(cursor.fetchone()["incasso_ingeschakeld"], 1)
