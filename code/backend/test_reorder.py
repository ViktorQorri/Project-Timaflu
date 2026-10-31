"""Case-based tests for the manually confirmed replenishment workflow."""

from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import DomainError
from services.reorder_service import ReorderService


class Stock:
    def shortages(self):
        return [{
            "product_id": 7,
            "productnaam": "Medicijn A",
            "voorraad": 2,
            "minimumvoorraad": 10,
            "tekort": 8,
        }]


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

    def record_order(self, supplier_id, product_id, quantity, confirmed):
        self.calls.append((supplier_id, product_id, quantity, confirmed))
        return 44

    def recorded_orders(self):
        return [{
            "inkoopbestelling_id": 44,
            "besteld_op": "2026-10-31 18:00:00",
            "status_naam": "besteld",
            "leverancier": "Goedkoop",
            "productnaam": "Medicijn A",
            "aantal": 8,
        }]


class ReorderTests(TestCase):
    def setUp(self):
        self.purchases = Purchases()
        self.service = ReorderService(Stock(), Suppliers(), self.purchases)

    def test_shortage_has_matching_offers_sorted_by_price(self):
        view = self.service.overview("7")
        self.assertEqual(view["selected"]["tekort"], 8)
        self.assertEqual([offer["leverancier_id"] for offer in view["offers"]], [2, 5])

    def test_only_current_shortages_can_be_selected(self):
        for value in ("8", "abc"):
            with self.assertRaises(DomainError):
                self.service.overview(value)

    def test_supplier_contact_and_valid_offer_are_required(self):
        with self.assertRaises(DomainError):
            self.service.record_confirmed("7", "2", "8", None)
        with self.assertRaises(DomainError):
            self.service.record_confirmed("8", "2", "8", "yes")
        with self.assertRaises(DomainError):
            self.service.record_confirmed("7", "99", "8", "yes")
        self.assertEqual(self.purchases.calls, [])

        self.assertEqual(self.service.record_confirmed("7", "2", "8", "yes"), 44)
        self.assertEqual(self.purchases.calls, [("2", "7", "8", "yes")])

    def test_reorder_page_renders_offers_and_recorded_orders(self):
        app = create_app()
        app.config.update(TESTING=True, SECRET_KEY="test-secret")
        with patch("routes.purchasing._reorder_service", return_value=self.service):
            with app.test_client() as client:
                response = client.get("/reorder?product_id=7")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Goedkoop", response.data)
        self.assertIn(b"laagste prijs", response.data)
        self.assertIn(b"Vastgelegde inkoopbestellingen", response.data)
        self.assertIn(b"besteld", response.data)

    def test_reorder_post_requires_contact_confirmation(self):
        app = create_app()
        app.testing = True
        app.config["SECRET_KEY"] = "test-secret"
        with patch("routes.purchasing._reorder_service", return_value=self.service):
            with app.test_client() as client:
                response = client.post("/reorder", data={
                    "product_id": "7", "supplier_id": "2", "quantity": "8",
                })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.purchases.calls, [])
