"""Manage customers tests (issue #8), without requiring a live MySQL server."""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, NotFoundError, ValidationError
from repositories.customer_repository import CustomerRepository
from services.customer_service import CustomerService


class Cursor:
    """Returns the prepared results in order, one per fetchone() or fetchall() call."""

    def __init__(self, results):
        self.results = list(results)
        self.commands = []
        self.lastrowid = 100

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        self.commands.append((" ".join(query.split()), params))
        if query.lstrip().startswith("INSERT"):
            self.lastrowid += 1

    def fetchone(self):
        return self.results.pop(0)

    def fetchall(self):
        return self.results.pop(0)


class Connection:
    def __init__(self, results=()):
        self.cur = Cursor(results)
        self.commits = 0
        self.rollbacks = 0

    def cursor(self, dictionary=False):
        assert dictionary
        return self.cur

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


VALID_FORM = {
    "bedrijfsnaam": "  Apotheek De Markt ",
    "contactpersoon": "J. Jansen",
    "telefoonnummer": "076 123 45 67",
    "afleveradres": "Markt 1, 4811 AA Breda",
    "factuuradres": "Postbus 10, 4800 AA Breda",
}

CURRENT = {
    "afleveradres_id": 7, "afleveradres": "Markt 1, 4811 AA Breda",
    "betaaladres_id": 8, "factuuradres": "Postbus 10, 4800 AA Breda",
}

CUSTOMER_ROW = {
    "klant_id": 1, "bedrijfsnaam": "Apotheek De Markt", "contactpersoon": "J. Jansen",
    "telefoonnummer": "076 123 45 67", "afleveradres": "Markt 1, 4811 AA Breda",
    "factuuradres": "Postbus 10, 4800 AA Breda", "jaaromzet": Decimal("12500.50"),
    "kortingspercentage": Decimal("10.00"),
}


def service(connection):
    return CustomerService(CustomerRepository(connection))


class CustomerOverviewTests(TestCase):
    def test_overview_shows_addresses_revenue_from_paid_invoices_and_discount(self):
        db = Connection([[CUSTOMER_ROW]])
        self.assertEqual(service(db).overview("  Markt ", 2026), [CUSTOMER_ROW])
        query, params = db.cur.commands[0]
        self.assertEqual(params, (2026, 2026, "%Markt%", "%Markt%", "%Markt%"))
        self.assertIn("JOIN Adres AS af ON af.adres_id = k.afleveradres_id", query)
        self.assertIn("JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id", query)
        self.assertIn("WHERE YEAR(f.betaald_op) = %s", query)
        self.assertIn("LEFT JOIN Klantkorting", query)

    def test_empty_search_matches_every_customer(self):
        db = Connection([[]])
        service(db).overview(None, 2026)
        self.assertEqual(db.cur.commands[0][1][2:], ("%%", "%%", "%%"))

    def test_unknown_customer_is_not_found(self):
        with self.assertRaises(NotFoundError):
            service(Connection([None])).get(99)


class CustomerValidationTests(TestCase):
    def test_valid_form_is_cleaned(self):
        customer = CustomerService(None).validate({**VALID_FORM, "contactpersoon": "  "})
        self.assertEqual(customer["bedrijfsnaam"], "Apotheek De Markt")
        self.assertIsNone(customer["contactpersoon"])

    def test_required_fields_are_reported_together(self):
        with self.assertRaises(ValidationError) as caught:
            CustomerService(None).validate({})
        self.assertEqual(len(caught.exception.messages), 4)
        self.assertIn("Bedrijfsnaam is verplicht.", caught.exception.messages)
        self.assertIn("Telefoonnummer is verplicht.", caught.exception.messages)
        self.assertIn("Afleveradres is verplicht.", caught.exception.messages)
        self.assertIn("Factuuradres is verplicht.", caught.exception.messages)

    def test_invalid_phone_numbers_are_rejected(self):
        for phone in ("abc-defg-hij", "12345", "076 123 45 67 ext 3"):
            with self.subTest(phone=phone), self.assertRaises(ValidationError):
                CustomerService(None).validate({**VALID_FORM, "telefoonnummer": phone})
        for phone in ("+31 76 123 4567", "(076) 123-45-67", "0612345678"):
            with self.subTest(phone=phone):
                CustomerService(None).validate({**VALID_FORM, "telefoonnummer": phone})

    def test_values_longer_than_the_schema_allows_are_rejected(self):
        with self.assertRaises(ValidationError) as caught:
            CustomerService(None).validate({**VALID_FORM, "bedrijfsnaam": "A" * 101, "afleveradres": "B" * 256})
        self.assertEqual(len(caught.exception.messages), 2)

    def test_invalid_form_does_not_touch_the_database(self):
        db = Connection()
        with self.assertRaises(ValidationError):
            service(db).create({**VALID_FORM, "bedrijfsnaam": ""})
        with self.assertRaises(ValidationError):
            service(db).update(1, {**VALID_FORM, "factuuradres": ""})
        self.assertFalse(db.cur.commands)
        self.assertEqual(db.commits, 0)


class CustomerWriteTests(TestCase):
    def test_create_registers_both_addresses_and_phone_number_in_one_transaction(self):
        db = Connection()
        self.assertEqual(service(db).create(VALID_FORM), 103)
        commands = db.cur.commands
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[0][1], ("Markt 1, 4811 AA Breda",))
        self.assertEqual(commands[1][1], ("Postbus 10, 4800 AA Breda",))
        self.assertIn("INSERT INTO Klant", commands[2][0])
        self.assertEqual(commands[2][1], ("Apotheek De Markt", "076 123 45 67", "J. Jansen", 101, 102))
        self.assertEqual((db.commits, db.rollbacks), (1, 0))

    def test_update_with_unchanged_addresses_keeps_address_rows(self):
        db = Connection([CURRENT])
        service(db).update(1, {**VALID_FORM, "telefoonnummer": "0612345678"})
        commands = db.cur.commands
        self.assertIn("FOR UPDATE", commands[0][0])
        self.assertEqual(len(commands), 2)
        self.assertIn("UPDATE Klant", commands[1][0])
        self.assertEqual(commands[1][1], ("Apotheek De Markt", "0612345678", "J. Jansen", 7, 8, 1))
        self.assertEqual(db.commits, 1)

    def test_update_with_new_delivery_address_adds_an_address_row(self):
        db = Connection([CURRENT])
        service(db).update(1, {**VALID_FORM, "afleveradres": "Markt 2, 4811 AA Breda"})
        commands = db.cur.commands
        self.assertEqual(len(commands), 3)
        self.assertEqual(commands[1], ("INSERT INTO Adres (adres) VALUES (%s)", ("Markt 2, 4811 AA Breda",)))
        self.assertEqual(commands[2][1][3:], (101, 8, 1))
        self.assertEqual(db.commits, 1)

    def test_update_of_unknown_customer_rolls_back(self):
        db = Connection([None])
        with self.assertRaises(NotFoundError):
            service(db).update(99, VALID_FORM)
        self.assertEqual((db.commits, db.rollbacks), (0, 1))
        self.assertEqual(len(db.cur.commands), 1)

    def test_delete_customer_without_history(self):
        db = Connection([{"klant_id": 1}, {"bestellingen": 0, "facturen": 0, "acquisities": 0}])
        service(db).delete(1)
        commands = [query for query, _ in db.cur.commands]
        self.assertIn("FOR UPDATE", commands[0])
        self.assertEqual(commands[2], "DELETE FROM Klantkorting WHERE klant_id = %s")
        self.assertEqual(commands[3], "DELETE FROM Klant WHERE klant_id = %s")
        self.assertEqual((db.commits, db.rollbacks), (1, 0))

    def test_customer_with_orders_or_invoices_is_not_deleted(self):
        db = Connection([{"klant_id": 1}, {"bestellingen": 2, "facturen": 1, "acquisities": 0}])
        with self.assertRaises(ConflictError):
            service(db).delete(1)
        self.assertFalse(any(query.startswith("DELETE") for query, _ in db.cur.commands))
        self.assertEqual((db.commits, db.rollbacks), (0, 1))

    def test_delete_unknown_customer(self):
        db = Connection([None])
        with self.assertRaises(NotFoundError):
            service(db).delete(99)
        self.assertEqual(db.rollbacks, 1)


class CustomerPageTests(TestCase):
    def setUp(self):
        app = create_app()
        app.testing = True
        self.client = app.test_client()

    def test_page_lists_customers_and_empty_state(self):
        with patch("routes.sales.get_connection", return_value=Connection([[CUSTOMER_ROW]])):
            response = self.client.get("/customers")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("Apotheek De Markt", page)
        self.assertIn("Postbus 10, 4800 AA Breda", page)
        self.assertIn("€ 12500,50", page)
        self.assertIn("10%", page)
        self.assertIn("Nieuwe klant", page)
        with patch("routes.sales.get_connection", return_value=Connection([[]])):
            response = self.client.get("/customers?q=Onbekend")
        self.assertIn("Geen klanten gevonden", response.get_data(as_text=True))

    def test_valid_new_customer_redirects_to_overview(self):
        db = Connection([[CUSTOMER_ROW]])
        with patch("routes.sales.get_connection", return_value=db):
            response = self.client.post("/customers", data=VALID_FORM)
            self.assertEqual(response.status_code, 302)
            self.assertTrue(response.headers["Location"].endswith("/customers"))
            page = self.client.get("/customers").get_data(as_text=True)
        self.assertEqual(db.commits, 1)
        self.assertIn("Klant 103 is aangemaakt.", page)

    def test_invalid_new_customer_shows_errors_and_keeps_input(self):
        db = Connection([[]])
        with patch("routes.sales.get_connection", return_value=db):
            response = self.client.post("/customers", data={**VALID_FORM, "telefoonnummer": ""})
        self.assertEqual(response.status_code, 400)
        page = response.get_data(as_text=True)
        self.assertIn("Telefoonnummer is verplicht.", page)
        self.assertIn('value="Markt 1, 4811 AA Breda"', page)
        self.assertEqual(db.commits, 0)

    def test_edit_form_is_filled_and_saves(self):
        with patch("routes.sales.get_connection", return_value=Connection([CUSTOMER_ROW])):
            response = self.client.get("/customers/1/edit")
        self.assertEqual(response.status_code, 200)
        self.assertIn('value="076 123 45 67"', response.get_data(as_text=True))
        db = Connection([CURRENT])
        with patch("routes.sales.get_connection", return_value=db):
            response = self.client.post("/customers/1/edit", data=VALID_FORM)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(db.commits, 1)

    def test_invalid_edit_shows_errors(self):
        with patch("routes.sales.get_connection", return_value=Connection()):
            response = self.client.post("/customers/1/edit", data={**VALID_FORM, "bedrijfsnaam": ""})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Bedrijfsnaam is verplicht.", response.get_data(as_text=True))

    def test_unknown_customer_gives_404(self):
        with patch("routes.sales.get_connection", return_value=Connection([None])):
            self.assertEqual(self.client.get("/customers/99/edit").status_code, 404)

    def test_delete_asks_for_confirmation_first(self):
        with patch("routes.sales.get_connection", return_value=Connection([CUSTOMER_ROW])):
            response = self.client.get("/customers/1/delete")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Klant verwijderen?", response.get_data(as_text=True))

    def test_delete_conflict_is_explained_on_overview(self):
        db = Connection([{"klant_id": 1}, {"bestellingen": 1, "facturen": 0, "acquisities": 0}, [CUSTOMER_ROW]])
        with patch("routes.sales.get_connection", return_value=db):
            response = self.client.post("/customers/1/delete")
            self.assertEqual(response.status_code, 302)
            page = self.client.get("/customers").get_data(as_text=True)
        self.assertIn("kan daarom niet worden verwijderd", page)
        self.assertEqual(db.commits, 0)
