"""Tests for acquisition visit registration and prospect follow-up."""

from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, DomainError, NotFoundError
from repositories.acquisition_repository import AcquisitionRepository
from services.acquisition_service import AcquisitionService


class FakeCursor:
    def __init__(self, rows=(), lastrowids=()):
        self.rows = list(rows)
        self.lastrowids = iter(lastrowids)
        self.lastrowid = None
        self.statements = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params=None):
        self.statements.append((query, params))
        self.lastrowid = next(self.lastrowids, None) if "INSERT INTO" in query else None

    def fetchone(self):
        return self.rows.pop(0) if self.rows else None

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows


class FakeConnection:
    def __init__(self, rows=(), lastrowids=()):
        self.cursor_instance = FakeCursor(rows, lastrowids)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        return self.cursor_instance

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


class AcquisitionRepositoryTests(TestCase):
    def test_follow_up_query_returns_rows_and_filters_due_prospects(self):
        rows = [{"potentiele_klant_id": 5, "bedrijfsnaam": "Apotheek A"}]
        connection = FakeConnection(rows)

        result = AcquisitionRepository(connection).find_due_follow_ups()

        self.assertEqual(result, rows)
        query = connection.cursor_instance.statements[0][0]
        self.assertIn("DATE_SUB(CURDATE(), INTERVAL 1 MONTH)", query)
        self.assertIn("NOT EXISTS", query)
        self.assertIn("p.status = 'open'", query)

    def test_register_prospect_saves_address_prospect_and_visit_together(self):
        connection = FakeConnection(lastrowids=[14, 8, 22])
        prospect = {
            "company_name": "Apotheek A",
            "contact_person": "A. Contact",
            "contact_details": "030-1234567",
            "address": "Voorbeeldstraat 1",
            "visit_date": date(2026, 10, 1),
        }

        prospect_id = AcquisitionRepository(connection).register_prospect(prospect)

        self.assertEqual(prospect_id, 8)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(connection.rollbacks, 0)
        statements = connection.cursor_instance.statements
        self.assertEqual(len(statements), 3)
        self.assertIn("INSERT INTO Adres", statements[0][0])
        self.assertIn("INSERT INTO PotentieleKlant", statements[1][0])
        self.assertEqual(statements[1][1][-1], 14)
        self.assertIn("INSERT INTO Acquisitiebezoek", statements[2][0])
        self.assertEqual(statements[2][1], (8, prospect["visit_date"]))

    def test_closing_follow_up_records_no_interest(self):
        connection = FakeConnection(
            rows=[
                {"klant_id": None, "status": "open", "bedrijfsnaam": "Apotheek A"},
                {"is_due": 1},
                None,
            ]
        )

        result = AcquisitionRepository(connection).complete_follow_up(
            8, "no_interest"
        )

        self.assertIsNone(result)
        self.assertEqual(connection.commits, 1)
        self.assertIn(
            "status = 'geen_interesse'",
            connection.cursor_instance.statements[-1][0],
        )

    def test_conversion_creates_customer_with_discount_and_links_prospect(self):
        connection = FakeConnection(
            rows=[
                {"klant_id": None, "status": "open", "bedrijfsnaam": "Apotheek A",
                 "contactpersoon": "A. Contact"},
                {"is_due": 1},
                None,
            ],
            lastrowids=[31, 32, 90],
        )
        customer = {
            "delivery_address": "Afleverstraat 1",
            "invoice_address": "Factuurstraat 1",
            "phone_number": "030-1234567",
        }

        customer_id = AcquisitionRepository(connection).complete_follow_up(
            8, "convert", customer
        )

        self.assertEqual(customer_id, 90)
        self.assertEqual(connection.commits, 1)
        statements = connection.cursor_instance.statements
        customer_insert = next(sql for sql, _ in statements if "INSERT INTO Klant" in sql)
        self.assertIn("eenmalige_korting_toegekend", customer_insert)
        self.assertIn("TRUE", customer_insert)
        self.assertIn("status = 'geconverteerd'", statements[-1][0])
        self.assertEqual(statements[-1][1], (90, 8))

    def test_unknown_prospect_rolls_back(self):
        connection = FakeConnection(rows=[None])

        with self.assertRaises(NotFoundError):
            AcquisitionRepository(connection).complete_follow_up(8, "no_interest")

        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)

    def test_follow_up_not_due_rolls_back(self):
        connection = FakeConnection(
            rows=[
                {"klant_id": None, "status": "open", "bedrijfsnaam": "Apotheek A"},
                {"is_due": 0},
            ]
        )

        with self.assertRaises(ConflictError):
            AcquisitionRepository(connection).complete_follow_up(8, "no_interest")

        self.assertEqual(connection.rollbacks, 1)

    def test_follow_up_with_existing_order_is_rejected(self):
        connection = FakeConnection(
            rows=[
                {"klant_id": 4, "status": "open", "bedrijfsnaam": "Apotheek A"},
                {"is_due": 1},
                {"bestelling_id": 15},
            ]
        )

        with self.assertRaises(ConflictError):
            AcquisitionRepository(connection).complete_follow_up(8, "no_interest")

        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(len(connection.cursor_instance.statements), 3)


class AcquisitionServiceTests(TestCase):
    def test_register_prospect_validates_and_parses_visit_date(self):
        class Repository:
            def register_prospect(self, prospect):
                self.prospect = prospect
                return 12

        repository = Repository()
        service = AcquisitionService(repository)
        form = {
            "company_name": " Apotheek A ",
            "contact_person": " A. Contact ",
            "contact_details": " 030-1234567 ",
            "address": " Voorbeeldstraat 1 ",
            "visit_date": "2026-10-01",
        }

        self.assertEqual(service.register_prospect(form), 12)
        self.assertEqual(repository.prospect["visit_date"], date(2026, 10, 1))
        self.assertEqual(repository.prospect["company_name"], "Apotheek A")

    def test_invalid_visit_date_is_rejected(self):
        class Repository:
            def register_prospect(self, _):
                raise AssertionError("invalid input must not reach the repository")

        with self.assertRaises(DomainError):
            AcquisitionService(Repository()).register_prospect(
                {
                    "company_name": "Apotheek A",
                    "contact_person": "A. Contact",
                    "contact_details": "030-1234567",
                    "address": "Voorbeeldstraat 1",
                    "visit_date": "not-a-date",
                }
            )

    def test_conversion_requires_both_customer_addresses(self):
        class Repository:
            def complete_follow_up(self, *_):
                raise AssertionError("invalid input must not reach the repository")

        with self.assertRaises(DomainError):
            AcquisitionService(Repository()).complete_follow_up(
                8,
                {
                    "outcome": "convert",
                    "delivery_address": "Afleverstraat 1",
                    "invoice_address": "",
                },
            )


class AcquisitionRouteTests(TestCase):
    def test_acquisition_page_renders_visit_form_and_empty_state(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection()

        with app.test_client() as client:
            with patch("routes.acquisition.get_connection", return_value=connection):
                response = client.get("/acquisition")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Bezoek registreren", response.data)
        self.assertIn(b"Er zijn geen potenti", response.data)

    def test_register_prospect_redirects_after_saving(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection(lastrowids=[14, 8, 22])

        with app.test_client() as client:
            with patch("routes.acquisition.get_connection", return_value=connection):
                response = client.post(
                    "/acquisition/prospects",
                    data={
                        "company_name": "Apotheek A",
                        "contact_person": "A. Contact",
                        "contact_details": "030-1234567",
                        "address": "Voorbeeldstraat 1",
                        "visit_date": "2026-10-01",
                    },
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/acquisition")
        self.assertEqual(connection.commits, 1)

    def test_conversion_route_creates_customer_and_redirects(self):
        app = create_app()
        app.testing = True
        connection = FakeConnection(
            rows=[
                {"klant_id": None, "status": "open", "bedrijfsnaam": "Apotheek A",
                 "contactpersoon": "A. Contact"},
                {"is_due": 1},
                None,
            ],
            lastrowids=[31, 32, 90],
        )

        with app.test_client() as client:
            with patch("routes.acquisition.get_connection", return_value=connection):
                response = client.post(
                    "/acquisition/prospects/8/follow-up",
                    data={
                        "outcome": "convert",
                        "delivery_address": "Afleverstraat 1",
                        "invoice_address": "Factuurstraat 1",
                        "phone_number": "030-1234567",
                    },
                )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/acquisition")
        self.assertEqual(connection.commits, 1)
