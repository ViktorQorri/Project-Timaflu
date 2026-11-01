"""Official Timaflu case: unpaid invoices and two manually sent reminders (issue #22)."""
from datetime import date, timedelta
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, DomainError, NotFoundError
from repositories.assessed_repository import AssessedRepository


INVOICE_DATE = date(2026, 10, 1)
TODAY = date(2026, 10, 12)


def unpaid_invoice(**updates):
    row = {
        "factuur_id": 7, "klant_id": 3, "factuurdatum": INVOICE_DATE,
        "betaald_op": None, "totaal_bedrag": Decimal("37.28"),
        "afzenderadres": "Testafzender 1", "factuuradres": "Teststraat 9, Breda",
        "huidig_factuuradres": "Nieuw adres", "bedrijfsnaam": "Apotheek casus",
        "incasso_ingeschakeld": False, "betalingsregeling_geaccepteerd": None,
        "eerste_herinnering": None, "tweede_herinnering": None
    }
    row.update(updates)
    return row


class ReadCursor:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, statement, params=()):
        self.statement, self.params = statement, params

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return self.rows


class ReadDB:
    def __init__(self, rows):
        self.cursor_instance = ReadCursor(rows)

    def cursor(self, dictionary=False):
        return self.cursor_instance


class ReminderCaseTests(TestCase):
    def test_overview_shows_only_unpaid_invoices_and_actual_reminder_dates(self):
        db = ReadDB([
            unpaid_invoice(totaal_bedrag=Decimal("37.28")),
            unpaid_invoice(factuur_id=8, factuurdatum=date(2026, 9, 29),
                           eerste_herinnering=date(2026, 10, 6)),
            unpaid_invoice(factuur_id=9, factuurdatum=date(2026, 9, 18),
                           eerste_herinnering=date(2026, 9, 25),
                           tweede_herinnering=date(2026, 10, 2)),
        ])
        rows = AssessedRepository(db).unpaid_invoice_overview(TODAY)
        self.assertEqual([r["weken_open"] for r in rows], [1, 1, 3])
        self.assertEqual([r["vervolgactie"] for r in rows],
                         ["eerste", "geen", "contact"])
        self.assertIn("f.betaald_op IS NULL", db.cursor_instance.statement)
        self.assertIn("Betalingsherinnering", db.cursor_instance.statement)

    def test_preview_uses_original_billing_address_and_persisted_total(self):
        db = ReadDB([unpaid_invoice()])
        doc = AssessedRepository(db).reminder_document(7, 1, TODAY)
        self.assertEqual(doc["ontvangeradres"], "Teststraat 9, Breda")
        self.assertEqual(doc["totaal_bedrag"], Decimal("37.28"))
        self.assertEqual(db.cursor_instance.params, (7,))
        self.assertIn("f.totaal_bedrag", db.cursor_instance.statement)

    def test_second_reminder_requires_first_sent_at_least_seven_days_earlier(self):
        first = date(2026, 10, 9)
        db = ReadDB([unpaid_invoice(eerste_herinnering=first)])
        repo = AssessedRepository(db)
        with self.assertRaisesRegex(DomainError, "minimaal een week"):
            repo.reminder_document(7, 2, date(2026, 10, 15))
        self.assertEqual(repo.reminder_document(
            7, 2, date(2026, 10, 16))["eerste_herinnering"], first)

    def test_first_and_second_reminders_only_in_their_case_weeks(self):
        repo = AssessedRepository(ReadDB([unpaid_invoice()]))
        with self.assertRaisesRegex(DomainError, "voorbij"):
            repo.reminder_document(7, 1, date(2026, 10, 15))
        repo = AssessedRepository(ReadDB([
            unpaid_invoice(eerste_herinnering=date(2026, 10, 9))
        ]))
        with self.assertRaisesRegex(DomainError, "voorbij"):
            repo.reminder_document(7, 2, date(2026, 10, 22))

    def test_commit_revalidates_collection_and_payment_plan_after_preview(self):
        class TransactionCursor:
            def __init__(self, invoice):
                self.invoice = invoice
                self.statements = []
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def execute(self, statement, parameters):
                self.statements.append(statement)
            def fetchone(self):
                return self.invoice

        class TransactionDB:
            def __init__(self, invoice):
                self.cursor_instance = TransactionCursor(invoice)
                self.rollbacks = 0
                self.commits = 0
            def cursor(self, dictionary=False):
                return self.cursor_instance
            def rollback(self):
                self.rollbacks += 1
            def commit(self):
                self.commits += 1

        cases = [
            unpaid_invoice(incasso_ingeschakeld=True),
            unpaid_invoice(betalingsregeling_geaccepteerd=True),
        ]
        for row in cases:
            with self.subTest(row=row):
                db = TransactionDB(row)
                with self.assertRaisesRegex(DomainError, "incasso of een betalingsregeling"):
                    AssessedRepository(db).record_payment_action(7, "reminder1", TODAY)
                self.assertEqual(db.rollbacks, 1)
                self.assertEqual(db.commits, 0)
                self.assertFalse(any(
                    "INSERT INTO Betalingsherinnering" in sql
                    for sql in db.cursor_instance.statements
                ))

    def test_paid_duplicate_unknown_and_unreliable_invoices_blocked(self):
        cases = [
            (unpaid_invoice(betaald_op=TODAY), DomainError),
            (unpaid_invoice(eerste_herinnering=TODAY), ConflictError),
            (unpaid_invoice(totaal_bedrag=None), DomainError),
            (unpaid_invoice(totaal_bedrag=Decimal("0")), DomainError),
            (unpaid_invoice(factuuradres="", huidig_factuuradres=""), DomainError),
            (unpaid_invoice(incasso_ingeschakeld=True), DomainError),
            (unpaid_invoice(betalingsregeling_geaccepteerd=True), DomainError),
        ]
        for invoice, error in cases:
            with self.subTest(invoice=invoice, error=error):
                with self.assertRaises(error):
                    AssessedRepository(ReadDB([invoice])).reminder_document(7, 1, TODAY)
        with self.assertRaises(NotFoundError):
            AssessedRepository(ReadDB([])).reminder_document(7, 1, TODAY)
        with self.assertRaises(DomainError):
            AssessedRepository(ReadDB([unpaid_invoice()])).reminder_document(
                7, 3, TODAY)

    def test_preview_cannot_be_created_before_one_week(self):
        with self.assertRaisesRegex(DomainError, "nog niet"):
            AssessedRepository(ReadDB([unpaid_invoice()])).reminder_document(
                7, 1, date(2026, 10, 7))
        with self.assertRaisesRegex(DomainError, "eerste"):
            AssessedRepository(ReadDB([unpaid_invoice()])).reminder_document(
                7, 2, date(2026, 10, 15))

    def test_open_overview_route_is_read_only(self):
        app = create_app()
        app.testing = True
        row = unpaid_invoice()
        row.update(weken_open=1, vervolgactie="eerste")
        with app.test_client() as client, patch(
            "routes.administration.get_connection", return_value=object()
        ), patch("routes.administration.AssessedRepository") as repository:
            repository.return_value.unpaid_invoice_overview.return_value = [row]
            response = client.get("/invoices/outstanding")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Apotheek casus", response.data)
        self.assertIn(b"Eerste herinnering voorbereiden", response.data)
        self.assertIn(b"37.28", response.data)
        self.assertNotIn(b"<script", response.data.lower())
        repository.return_value.record_payment_action.assert_not_called()

    def test_print_preview_does_not_mark_a_reminder_as_sent(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client, patch(
            "routes.administration.get_connection", return_value=object()
        ), patch("routes.administration.AssessedRepository") as repository:
            repository.return_value.reminder_document.return_value = {
                **unpaid_invoice(), "ontvangeradres": "Teststraat 9, Breda"
            }
            response = client.get("/invoices/7/reminders/1")
        self.assertEqual(response.status_code, 200)
        for text in (b"Teststraat 9, Breda", b"37.28", b"print",
                     b"Eerste betalingsherinnering", b"sent_confirmed"):
            self.assertIn(text.lower(), response.data.lower())
        self.assertNotIn(b"<script", response.data.lower())
        repository.return_value.record_payment_action.assert_not_called()

    def test_only_explicit_dispatch_confirmation_records_sent_date(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            refused = client.post("/invoices/7/reminders/1/sent", data={})
            self.assertEqual(refused.status_code, 400)
            with patch("routes.administration.get_connection", return_value=object()
            ), patch("routes.administration.AssessedRepository") as repository:
                confirmed = client.post("/invoices/7/reminders/1/sent",
                                        data={"sent_confirmed": "yes"})
                self.assertEqual(confirmed.status_code, 302)
                self.assertIn("/invoices/outstanding", confirmed.headers["Location"])
                repository.return_value.reminder_document.assert_called_once()
                args = repository.return_value.record_payment_action.call_args.args
                self.assertEqual(args[:2], (7, "reminder1"))

    def test_collection_refusal_can_be_confirmed_in_the_existing_invoice_form(self):
        source = create_app().jinja_loader.get_source(
            create_app().jinja_env, "invoices.html"
        )[0]
        self.assertIn('name="offer_refused_confirmed"', source)
        self.assertIn('name="agency_acceptance_confirmed"', source)
        self.assertIn("Betalingsregeling geweigerd", source)
        self.assertIn('name="received_amount"', source)

    def test_old_invoice_form_can_no_longer_skip_the_dispatch_step(self):
        app = create_app()
        app.testing = True
        with app.test_client() as client:
            for action in ("reminder1", "reminder2"):
                response = client.post("/invoices/actions", data={
                    "customer_id": "3", "invoice_id": "7", "action": action
                })
                self.assertEqual(response.status_code, 400)
        template = app.jinja_env.get_template("invoices.html")
        # The options must no longer exist, even when an employee views invoices.
        source = app.jinja_loader.get_source(app.jinja_env, "invoices.html")[0]
        self.assertNotIn('<option value="reminder1">', source)
        self.assertNotIn('<option value="reminder2">', source)
