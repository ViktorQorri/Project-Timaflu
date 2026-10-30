"""Case-based tests for the manual replenishment workflow (#57)."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from services.reorder_service import ReorderService


class Stock:
    def shortages(self):
        return [{"product_id": 7, "productnaam": "Medicijn A",
                 "voorraad": 2, "minimumvoorraad": 10, "tekort": 8}]


class Suppliers:
    def offers_for_product(self, name):
        return [
            {"product_id": 7, "leverancier_id": 2, "leverancier": "Goedkoop",
             "contactpersoon": "Sam", "telefoonnummer": "0700000000",
             "inkoopprijs": 5},
            {"product_id": 7, "leverancier_id": 5, "leverancier": "Duurder",
             "contactpersoon": "Ria", "telefoonnummer": "0701111111",
             "inkoopprijs": 8},
            {"product_id": 8, "leverancier_id": 1, "leverancier": "Andere",
             "contactpersoon": "Leo", "telefoonnummer": "0702222222",
             "inkoopprijs": 1},
        ]


class Purchases:
    def __init__(self):
        self.calls = []

    def record_order(self, supplier_id, product_id, quantity):
        self.calls.append((supplier_id, product_id, quantity))
        return 44


class ReorderTests(TestCase):
    def setUp(self):
        self.purchases = Purchases()
        self.service = ReorderService(Stock(), Suppliers(), self.purchases)

    def test_select_shortage_and_sorted_matching_offers(self):
        view = self.service.overview("7")
        self.assertEqual(view["selected"]["tekort"], 8)
        self.assertEqual([r["leverancier_id"] for r in view["offers"]], [2, 5])

    def test_reject_non_shortage(self):
        for value in ("8", "abc"):
            with self.assertRaises(DomainError):
                self.service.overview(value)

    def test_requires_supplier_contact_confirmation(self):
        with self.assertRaises(DomainError):
            self.service.record_confirmed("7", "2", "8", None)
        self.assertEqual(self.purchases.calls, [])
        self.assertEqual(self.service.record_confirmed("7", "2", "8", "yes"), 44)

    def test_get_renders_and_post_requires_confirmation(self):
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        with patch("routes.purchasing._reorder_service", return_value=self.service):
            with app.test_client() as client:
                response = client.get("/reorder?product_id=7")
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Goedkoop", response.data)
                self.assertIn(b"Fabrikant heeft deze bestelling bevestigd", response.data)
                response = client.post("/reorder", data={
                    "product_id": "7", "supplier_id": "2", "quantity": "8"
                })
                self.assertEqual(response.status_code, 400)
                self.assertEqual(self.purchases.calls, [])
                response = client.post("/reorder", data={
                    "product_id": "7", "supplier_id": "2", "quantity": "8",
                    "confirmed": "yes",
                })
                self.assertEqual(response.status_code, 302)
                self.assertEqual(len(self.purchases.calls), 1)
