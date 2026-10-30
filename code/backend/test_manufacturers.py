"""Focused validation and screen tests for issue #14."""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from services.manufacturer_service import ManufacturerService


class FakeManufacturers:
    def __init__(self):
        self.created = None
        self.updated = None
        self.priced = None

    def all(self):
        return [{"leverancier_id": 3, "naam": "Fabrikant A", "adres": "Straat 1",
                 "contactpersoon": "Eva", "telefoonnummer": "0123456789",
                 "internetadres": ""}]

    def get(self, supplier_id):
        return self.all()[0] if supplier_id == 3 else None

    def create(self, data):
        self.created = data
        return 3

    def update(self, ident, data):
        self.updated = (ident, data)
        return ident == 3

    def products(self):
        return [{"product_id": 2, "productnaam": "Medicijn", "artikelnummer": "M2"}]

    def offers(self, supplier_id):
        return [{"product_id": 2, "productnaam": "Medicijn", "inkoopprijs": Decimal("10.50")}]

    def set_price(self, supplier_id, product_id, price):
        self.priced = (supplier_id, product_id, price)


class ManufacturerTests(TestCase):
    def setUp(self):
        self.repo = FakeManufacturers()
        self.service = ManufacturerService(self.repo)

    def test_invalid_manufacturer_refused(self):
        for values in [{"naam": "", "adres": "Straat 1"},
                       {"naam": "A", "adres": ""},
                       {"naam": "X" * 101, "adres": "Straat 1"}]:
            with self.assertRaises(DomainError):
                self.service.create(values)
        self.assertIsNone(self.repo.created)

    def test_create_and_edit_valid_manufacturer(self):
        data = {"naam": "Fabrikant A", "adres": "Straat 1",
                "contactpersoon": "Eva", "telefoonnummer": "0123456789"}
        self.assertEqual(self.service.create(data), 3)
        self.assertEqual(self.repo.created["naam"], "Fabrikant A")
        self.service.update(3, data)
        self.assertEqual(self.repo.updated[0], 3)

    def test_price_validation_and_update(self):
        for val in ["-0.01", "abc", "12.345", "NaN", "Infinity"]:
            with self.assertRaises(DomainError):
                self.service.set_price(3, 2, val)
        self.service.set_price(3, 2, "10,50")
        self.assertEqual(self.repo.priced, (3, 2, Decimal("10.50")))

    def test_pages_and_validation_response(self):
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-key")
        with patch("routes.purchasing._manufacturer_service", return_value=self.service):
            with app.test_client() as client:
                response = client.get("/manufacturers")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Fabrikant A", response.data)
                response = client.get("/manufacturers/3/prices")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Medicijn", response.data)
                response = client.post("/manufacturers/new", data={"naam": "X"})
                self.assertEqual(response.status_code, 400)
                self.assertIn(b"Naam en adres zijn verplicht", response.data)
                response = client.post("/manufacturers/3/prices",
                                       data={"product_id": "2", "price": "11,20"})
                self.assertEqual(response.status_code, 302)
                self.assertEqual(self.repo.priced[2], Decimal("11.20"))
