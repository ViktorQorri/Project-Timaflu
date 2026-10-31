"""Weekly invoices use only delivered, unbilled lines and saved amount snapshots."""

from datetime import date
from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


DELIVERED_LINES = [
    {
        "levering_id": 4,
        "product_id": 2,
        "quantity": 2,
        "unit_price": Decimal("20.00"),
        "eenmalige_korting_toegepast": True,
    }
]


class InvoiceCursor:
    def __init__(self, database):
        self.database = database
        self.rowcount = 1
        self.lastrowid = None
        self.query = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=()):
        self.query = query
        self.database.statements.append((query, params))
        if "INSERT INTO Factuur" in query:
            self.lastrowid = 50

    def fetchone(self):
        if "FROM Klant AS k" in self.query:
            return {"klant_id": 1, "bedrijfsnaam": "Testapotheek", "adres": "Teststraat 1"}
        if "AS bekende_kortingen" in self.query:
            return self.database.discount_history
        if "AS paid_count" in self.query:
            return {"paid_count": 0, "known_amount_count": 0, "jaaromzet": Decimal("0.00")}
        if "SELECT factuur_id, totaal_bedrag" in self.query:
            return {"factuur_id": 50, "totaal_bedrag": None}
        return None

    def fetchall(self):
        if "FROM Leveringregel AS lr" in self.query:
            return self.database.lines
        return []


class InvoiceDatabase:
    def __init__(self, lines=None, discount_history=None):
        self.lines = DELIVERED_LINES if lines is None else lines
        self.discount_history = discount_history or {
            "aantal_facturen": 0,
            "bekende_kortingen": 0,
            "korting_al_toegepast": 0,
        }
        self.statements = []
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return InvoiceCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class InvoiceIssuanceTests(TestCase):
    def test_weekly_invoice_snapshots_only_the_new_delivered_lines(self):
        database = InvoiceDatabase()

        invoice_id = AssessedRepository(database).create_weekly_invoice(
            1, date(2026, 10, 26), date(2026, 10, 30)
        )

        self.assertEqual(invoice_id, 50)
        self.assertEqual(database.commits, 1)
        self.assertEqual(database.rollbacks, 0)
        line_query = next(
            query for query, _ in database.statements if "FROM Leveringregel AS lr" in query
        )
        self.assertIn("lr.factuur_id IS NULL", line_query)
        self.assertIn("lp.resultaat = 'afgeleverd'", line_query)
        update = next(
            (query, params)
            for query, params in database.statements
            if "SET factuur_id = %s" in query
        )
        self.assertEqual(update[1], (50, 4, 2))
        snapshot = next(
            params
            for query, params in database.statements
            if "UPDATE Factuur SET bedrag_excl_btw" in query
        )
        self.assertEqual(snapshot[-2:], (Decimal("37.28"), 50))

    def test_previous_invoice_with_unknown_one_time_discount_blocks_recalculation(self):
        database = InvoiceDatabase(
            discount_history={
                "aantal_facturen": 1,
                "bekende_kortingen": 0,
                "korting_al_toegepast": 0,
            }
        )

        with self.assertRaises(DomainError):
            AssessedRepository(database).create_weekly_invoice(
                1, date(2026, 10, 26), date(2026, 10, 30)
            )

        self.assertEqual(database.commits, 0)
        self.assertEqual(database.rollbacks, 1)
        self.assertFalse(any("INSERT INTO Factuur" in query for query, _ in database.statements))

    def test_one_time_discount_is_not_reapplied_to_a_later_week(self):
        database = InvoiceDatabase(
            discount_history={
                "aantal_facturen": 1,
                "bekende_kortingen": 1,
                "korting_al_toegepast": 1,
            }
        )

        AssessedRepository(database).create_weekly_invoice(
            1, date(2026, 11, 2), date(2026, 11, 6)
        )

        snapshot = next(
            params
            for query, params in database.statements
            if "UPDATE Factuur SET bedrag_excl_btw" in query
        )
        self.assertEqual(snapshot[-2], Decimal("41.42"))

    def test_no_delivered_lines_does_not_create_an_invoice(self):
        database = InvoiceDatabase(lines=[])

        with self.assertRaises(DomainError):
            AssessedRepository(database).create_weekly_invoice(
                1, date(2026, 10, 26), date(2026, 10, 30)
            )

        self.assertEqual(database.commits, 0)
        self.assertEqual(database.rollbacks, 1)

    def test_create_route_uses_monday_of_selected_week(self):
        app = create_app()
        app.testing = True

        with app.test_client() as client:
            with patch("routes.administration.get_connection", return_value=object()):
                with patch("routes.administration.AssessedRepository") as repository:
                    repository.return_value.create_weekly_invoice.return_value = 50
                    response = client.post(
                        "/invoices/create",
                        data={"customer_id": "1", "week_of": "2026-10-30"},
                    )

        self.assertEqual(response.status_code, 302)
        args = repository.return_value.create_weekly_invoice.call_args.args
        self.assertEqual(args[:2], (1, date(2026, 10, 26)))

    def test_manual_discount_preview_uses_invoice_discount_sequence(self):
        app = create_app()
        app.testing = True
        assessed = type(
            "AssessedStub",
            (),
            {
                "customer_revenue": lambda self, customer_id, year: (
                    {"klant_id": customer_id, "bedrijfsnaam": "Testapotheek"},
                    Decimal("0.00"),
                ),
                "customer_order_count": lambda self, customer_id: 0,
            },
        )()

        with app.test_client() as client:
            with patch("routes.sales.get_connection", return_value=object()):
                with patch("routes.sales.AssessedRepository", return_value=assessed):
                    response = client.post(
                        "/orders/calculate-discount",
                        data={"customer_id": "1", "subtotal": "40.00"},
                    )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"9% btw", response.data)
        self.assertIn(b"De eenmalige korting en klantenkorting", response.data)
        self.assertIn(b"37.28", response.data)
