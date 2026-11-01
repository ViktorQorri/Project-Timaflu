"""Ensure medicines with more than two active ingredients can be entered without JS."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from app import create_app

class FakeProductService:
    def __init__(self):
        self.saved = False
    def suppliers(self):
        return [SimpleNamespace(supplier_id=1, name="Testfabrikant")]
    def get_product(self, product_id):
        return SimpleNamespace(product_id=product_id, product_name="Testmedicijn")
    def add_product(self, data):
        self.saved = True
    def update_product(self, product_id, data):
        self.saved = True

class ActiveIngredientFormTests(TestCase):
    def test_create_form_expands_while_preserving_fields(self):
        app = create_app()
        app.config.update(TESTING=True)
        service = FakeProductService()
        with patch("routes.purchasing.product_service", return_value=service):
            with app.test_client() as client:
                response = client.post("/products/new", data={
                    "form_action": "add_ingredient",
                    "ingredient_rows": "2",
                    "product_name": "Medicijn ABC",
                    "ingredient_name": ["Stof A", "Stof B"],
                    "ingredient_quantity": ["20 mg", "30 mg"],
                })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'name="ingredient_name"'), 3)
        self.assertIn(b'value="Stof B"', response.data)
        self.assertIn(b'value="Medicijn ABC"', response.data)
        self.assertFalse(service.saved)

    def test_edit_form_expands_without_writing_product(self):
        app = create_app()
        app.config.update(TESTING=True)
        service = FakeProductService()
        with patch("routes.purchasing.product_service", return_value=service):
            with app.test_client() as client:
                response = client.post("/products/1/edit", data={
                    "form_action": "add_ingredient", "ingredient_rows": "3",
                    "ingredient_name": ["Stof A", "Stof B", "Stof C"],
                    "ingredient_quantity": ["10 mg", "20 mg", "30 mg"],
                })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'name="ingredient_name"'), 4)
        self.assertIn(b'value="Stof C"', response.data)
        self.assertFalse(service.saved)

    def test_untrusted_row_counter_does_not_expand_form(self):
        app = create_app()
        app.config.update(TESTING=True)
        service = FakeProductService()
        with patch("routes.purchasing.product_service", return_value=service):
            with app.test_client() as client:
                response = client.post("/products/new", data={
                    "form_action": "add_ingredient",
                    "ingredient_rows": "1000000000",
                    "ingredient_name": ["Stof A", ""],
                    "ingredient_quantity": ["20 mg", ""],
                })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'name="ingredient_name"'), 3)
        self.assertFalse(service.saved)

    def test_more_than_sixty_four_active_ingredients_can_be_entered(self):
        app = create_app()
        app.config.update(TESTING=True)
        service = FakeProductService()
        with patch("routes.purchasing.product_service", return_value=service):
            with app.test_client() as client:
                response = client.post("/products/new", data={
                    "form_action": "add_ingredient",
                    "ingredient_name": [f"Stof {i}" for i in range(65)],
                    "ingredient_quantity": ["1 mg"] * 65,
                })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.count(b'name="ingredient_name"'), 66)
        self.assertFalse(service.saved)

    def test_ingredient_may_be_entered_in_second_row(self):
        app = create_app()
        app.config.update(TESTING=True)
        service = FakeProductService()
        with patch("routes.purchasing.product_service", return_value=service):
            with app.test_client() as client:
                response = client.get("/products/new")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b'name="ingredient_name" value="" maxlength="100" required', response.data)
        self.assertNotIn(b'name="ingredient_quantity" value="" maxlength="50" placeholder="500 mg" required', response.data)
