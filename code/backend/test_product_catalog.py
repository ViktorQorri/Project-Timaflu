"""Tests for the product catalog (issue #13), without requiring a live MySQL server."""

from decimal import Decimal
from unittest import TestCase
from unittest.mock import patch

from app import create_app
from domain.errors import ConflictError, DomainError, NotFoundError
from domain.product import Product, ProductActiveIngredient, SupplierOffer
from domain.supplier import Supplier
from repositories.product_repository import ProductRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from repositories.sales_stock_repository import SalesStockRepository
from repositories.stock_repository import StockRepository
from repositories.supplier_repository import SupplierRepository
from services.product_service import ProductService, read_product


def form_data(**changes):
    data = {
        "article_number": "TIM-1001",
        "order_code": "BC-1001",
        "product_name": "Paracetamol 500 mg",
        "price_per_bulk_package": "24,50",
        "package_type": "box",
        "number_of_retail_packages": "20",
        "short_description": "Pain relief",
        "long_description": "",
        "minimum_order_quantity": "5",
        "minimum_stock": "40",
        "ingredient_name": ["paracetamol", "", ""],
        "ingredient_quantity": ["500 mg", "", ""],
        "supplier_id": "1",
        "purchase_price": "18.75",
        "director_approved": "yes",
    }
    data.update(changes)
    return data


def product(product_id=1):
    return Product(
        product_id=product_id, article_number="TIM-1001", order_code="BC-1001",
        product_name="Paracetamol 500 mg", price_per_bulk_package=Decimal("24.50"),
        package_type="box", number_of_retail_packages=20, short_description="Pain relief",
        long_description=None, minimum_order_quantity=5, minimum_stock=40,
        active_ingredients=[ProductActiveIngredient("paracetamol", "500 mg")],
    )


class FakeProductRepository:
    def __init__(self, products=None, code_owners=None):
        self.products = {p.product_id: p for p in (products or [])}
        self.code_owners = code_owners or []
        self.added = None
        self.updated = None
        self.removed = None

    def list_in_assortment(self):
        return list(self.products.values())

    def get_by_id(self, product_id):
        return self.products.get(product_id)

    def find_code_owners(self, article_number, order_code, exclude_product_id=None):
        return self.code_owners

    def add(self, new_product, offer):
        self.added = (new_product, offer)
        return 7

    def update(self, changed_product):
        self.updated = changed_product
        return changed_product.product_id in self.products

    def remove_from_assortment(self, product_id):
        self.removed = product_id
        return self.products.pop(product_id, None) is not None


class FakeSupplierRepository:
    def __init__(self, suppliers=None):
        self.suppliers = suppliers if suppliers is not None else [
            Supplier(1, "Pharma Supply BV", "Anna", "0123", None)
        ]

    def list_all(self):
        return self.suppliers

    def get_by_id(self, supplier_id):
        return next((s for s in self.suppliers if s.supplier_id == supplier_id), None)


class RecordingCursor:
    """Records every statement; fetches return the queued result sets in order."""

    def __init__(self, results=None):
        self.statements = []
        self.results = list(results or [])
        self.lastrowid = 7
        self.rowcount = 1

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=None):
        self.statements.append((" ".join(sql.split()), params))

    def fetchall(self):
        return self.results.pop(0) if self.results else []

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


class RecordingConnection:
    def __init__(self, results=None, fail_on=None):
        self.cur = RecordingCursor(results)
        self.fail_on = fail_on
        self.committed = False
        self.rolled_back = False
        if fail_on:
            original = self.cur.execute

            def execute(sql, params=None):
                original(sql, params)
                if fail_on in sql:
                    raise RuntimeError("database failure")

            self.cur.execute = execute

    def cursor(self, dictionary=False):
        return self.cur

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


class ReadProductTests(TestCase):
    def test_reads_valid_data_and_skips_empty_ingredient_rows(self):
        result = read_product(form_data())
        self.assertEqual(result.price_per_bulk_package, Decimal("24.50"))
        self.assertEqual(result.number_of_retail_packages, 20)
        self.assertIsNone(result.long_description)
        self.assertEqual(result.active_ingredients, [ProductActiveIngredient("paracetamol", "500 mg")])

    def test_rejects_invalid_values(self):
        cases = {
            "required name": form_data(product_name="  "),
            "price text": form_data(price_per_bulk_package="abc"),
            "negative price": form_data(price_per_bulk_package="-1"),
            "three decimals": form_data(price_per_bulk_package="1.005"),
            "no retail packages": form_data(number_of_retail_packages="0"),
            "minimum order zero": form_data(minimum_order_quantity="0"),
            "negative minimum stock": form_data(minimum_stock="-1"),
            "too long code": form_data(article_number="X" * 51),
            "no ingredient": form_data(ingredient_name=[""], ingredient_quantity=[""]),
            "half ingredient": form_data(ingredient_name=["a", "b"], ingredient_quantity=["1 mg", ""]),
            "double ingredient": form_data(
                ingredient_name=["Codeine", "codeine"], ingredient_quantity=["1 mg", "2 mg"]
            ),
        }
        for name, data in cases.items():
            with self.subTest(name), self.assertRaises(DomainError):
                read_product(data)


class ProductServiceTests(TestCase):
    def test_add_product_saves_product_and_supplier_offer(self):
        products = FakeProductRepository()
        product_id = ProductService(products, FakeSupplierRepository()).add_product(form_data())
        self.assertEqual(product_id, 7)
        saved, offer = products.added
        self.assertEqual(saved.article_number, "TIM-1001")
        self.assertEqual(offer, SupplierOffer(1, Decimal("18.75")))

    def test_add_product_requires_an_existing_supplier(self):
        products = FakeProductRepository()
        service = ProductService(products, FakeSupplierRepository())
        with self.assertRaises(DomainError):
            service.add_product(form_data(supplier_id="99"))
        with self.assertRaises(DomainError):
            service.add_product(form_data(supplier_id=""))
        self.assertIsNone(products.added)

    def test_used_article_number_is_a_conflict_even_for_removed_products(self):
        owner = {"product_id": 3, "artikelnummer": "TIM-1001", "bestelcode": "OTHER",
                 "productnaam": "Old paracetamol", "in_assortiment": 0}
        products = FakeProductRepository(code_owners=[owner])
        with self.assertRaisesRegex(ConflictError, "verwijderd uit het assortiment"):
            ProductService(products, FakeSupplierRepository()).add_product(form_data())
        self.assertIsNone(products.added)

    def test_update_unknown_product_is_not_found(self):
        service = ProductService(FakeProductRepository(), FakeSupplierRepository())
        with self.assertRaises(NotFoundError):
            service.update_product(5, form_data())

    def test_remove_from_assortment(self):
        products = FakeProductRepository([product()])
        service = ProductService(products, FakeSupplierRepository())
        self.assertEqual(service.remove_from_assortment(1).product_name, "Paracetamol 500 mg")
        with self.assertRaises(NotFoundError):
            service.remove_from_assortment(1)


class ProductRepositoryTests(TestCase):
    def test_add_runs_in_one_transaction(self):
        connection = RecordingConnection()
        offer = SupplierOffer(1, Decimal("18.75"))
        self.assertEqual(ProductRepository(connection).add(product(None), offer), 7)
        sql = [statement for statement, _ in connection.cur.statements]
        self.assertTrue(sql[0].startswith("INSERT INTO Product"))
        self.assertTrue(sql[1].startswith("INSERT INTO ProductWerkzameStof"))
        self.assertTrue(sql[2].startswith("INSERT INTO LeveranciersAanbod"))
        self.assertEqual(connection.cur.statements[2][1], (1, 7, Decimal("18.75")))
        self.assertTrue(connection.committed)

    def test_add_rolls_back_when_a_statement_fails(self):
        connection = RecordingConnection(fail_on="LeveranciersAanbod")
        with self.assertRaises(RuntimeError):
            ProductRepository(connection).add(product(None), SupplierOffer(1, Decimal("1")))
        self.assertTrue(connection.rolled_back)
        self.assertFalse(connection.committed)

    def test_remove_keeps_the_row(self):
        connection = RecordingConnection()
        self.assertTrue(ProductRepository(connection).remove_from_assortment(1))
        statement, params = connection.cur.statements[0]
        self.assertTrue(statement.startswith("UPDATE Product SET in_assortiment = FALSE"))
        self.assertNotIn("DELETE", statement)
        self.assertEqual(params, (1,))

    def test_update_of_removed_product_changes_nothing(self):
        connection = RecordingConnection(results=[[]])
        self.assertFalse(ProductRepository(connection).update(product()))
        self.assertEqual(len(connection.cur.statements), 1)
        self.assertTrue(connection.rolled_back)

    def test_list_attaches_ingredients_and_skips_removed_products(self):
        row = {"product_id": 1, "artikelnummer": "TIM-1001", "bestelcode": "BC-1001",
               "productnaam": "Paracetamol", "prijs_per_grootverpakking": Decimal("24.50"),
               "verpakkingssoort": "box", "aantal_detailverpakkingen": 20,
               "korte_omschrijving": None, "lange_omschrijving": None,
               "minimale_bestelhoeveelheid": 5, "minimumvoorraad": 40, "in_assortiment": 1}
        ingredient = {"product_id": 1, "stofnaam": "paracetamol", "hoeveelheid": "500 mg"}
        connection = RecordingConnection(results=[[row], [ingredient]])
        products = ProductRepository(connection).list_in_assortment()
        self.assertEqual(products[0].active_ingredients[0].quantity, "500 mg")
        for statement, _ in connection.cur.statements:
            self.assertIn("in_assortiment = TRUE", statement)


class RemovedProductsElsewhereTests(TestCase):
    """A removed product must not be sold, reordered or shown as a shortage."""

    def test_other_queries_leave_out_removed_products(self):
        checks = [
            (StockRepository, lambda r: r.list_stock_below_minimum()),
            (SalesStockRepository, lambda r: r.find_products("para")),
            (SupplierRepository, lambda r: r.find_offers("para")),
        ]
        for repository, call in checks:
            with self.subTest(repository.__name__):
                connection = RecordingConnection()
                call(repository(connection))
                self.assertIn("p.in_assortiment = TRUE", connection.cur.statements[0][0])

    def test_purchase_order_for_removed_product_is_refused(self):
        connection = RecordingConnection(results=[[]])
        with self.assertRaises(DomainError):
            PurchaseOrderRepository(connection).create(1, 1, 10)
        self.assertIn("p.in_assortiment = TRUE", connection.cur.statements[0][0])
        self.assertEqual(len(connection.cur.statements), 1)


class ProductPageTests(TestCase):
    def setUp(self):
        app = create_app()
        app.testing = True
        self.client = app.test_client()
        self.products = FakeProductRepository([product()])
        self.suppliers = FakeSupplierRepository()
        patches = [
            patch("routes.purchasing.get_connection", return_value=None),
            patch("routes.purchasing.ProductRepository", return_value=self.products),
            patch("routes.purchasing.SupplierRepository", return_value=self.suppliers),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_catalog_lists_products(self):
        response = self.client.get("/products")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Paracetamol 500 mg", response.data)
        self.assertIn(b"paracetamol 500 mg", response.data)
        self.assertIn(b"/products/1/edit", response.data)

    def test_add_form_shows_suppliers(self):
        response = self.client.get("/products/new")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Pharma Supply BV", response.data)

    def test_add_without_suppliers_explains_why(self):
        self.suppliers.suppliers = []
        response = self.client.get("/products/new")
        self.assertIn(b"Nog geen leveranciers", response.data)
        self.assertNotIn(b"<form class=\"product-form\"", response.data)

    def test_valid_add_redirects_to_catalog(self):
        response = self.client.post("/products/new", data=form_data())
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.headers["Location"].endswith("/products"))
        self.assertEqual(self.products.added[0].product_name, "Paracetamol 500 mg")

    def test_invalid_add_shows_error_and_keeps_input(self):
        response = self.client.post(
            "/products/new", data=form_data(price_per_bulk_package="abc", product_name="Ibuprofen")
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("moet een bedrag zijn".encode(), response.data)
        self.assertIn(b'value="Ibuprofen"', response.data)
        self.assertIsNone(self.products.added)

    def test_edit_form_is_filled_and_saves(self):
        response = self.client.get("/products/1/edit")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'value="TIM-1001"', response.data)
        self.assertNotIn(b"Eerste leverancier", response.data)
        response = self.client.post("/products/1/edit", data=form_data(minimum_stock="60"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.products.updated.minimum_stock, 60)

    def test_remove_asks_for_confirmation_first(self):
        response = self.client.get("/products/1/remove")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Verwijderen uit assortiment", response.data)
        self.assertIsNone(self.products.removed)
        response = self.client.post("/products/1/remove")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.products.removed, 1)

    def test_unknown_product_is_not_found(self):
        self.assertEqual(self.client.get("/products/9/edit").status_code, 404)
        self.assertEqual(self.client.post("/products/9/remove").status_code, 404)
