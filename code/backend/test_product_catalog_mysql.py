"""Opt-in MySQL 8.4 integration tests for issue #13.

These tests only run against the disposable database explicitly named below.
To run, start an isolated localhost MySQL instance and set TIMAFLU_TEST_MYSQL,
TIMAFLU_TEST_HOST, TIMAFLU_TEST_PORT, TIMAFLU_TEST_USER,
TIMAFLU_TEST_PASSWORD and TIMAFLU_TEST_DATABASE. No existing DB is reset.
"""

import os
from pathlib import Path
import unittest
from uuid import uuid4

import mysql.connector

from domain.errors import ConflictError, DomainError, NotFoundError
from domain.product import SupplierOffer
from repositories.product_repository import ProductRepository
from repositories.purchase_order_repository import PurchaseOrderRepository
from repositories.sales_stock_repository import SalesStockRepository
from repositories.stock_repository import StockRepository
from repositories.supplier_repository import SupplierRepository
from services.product_service import ProductService, read_product


ROOT = Path(__file__).resolve().parents[2]
TEST_DB = "timaflu_pr101_isolated"


@unittest.skipUnless(
    os.getenv("TIMAFLU_TEST_MYSQL") == "isolated"
    and os.getenv("TIMAFLU_TEST_HOST") == "127.0.0.1"
    and os.getenv("TIMAFLU_TEST_DATABASE") == TEST_DB,
    "Requires an explicitly named disposable local MySQL database",
)
class ProductCatalogMySQLTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.options = {
            "host": "127.0.0.1",
            "port": int(os.environ["TIMAFLU_TEST_PORT"]),
            "user": os.environ["TIMAFLU_TEST_USER"],
            "password": os.getenv("TIMAFLU_TEST_PASSWORD", ""),
            "database": TEST_DB,
        }
        connection = mysql.connector.connect(**cls.options)
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = %s", (TEST_DB,)
                )
                if cursor.fetchone()[0] == 0:
                    schema = (ROOT / "code/database/schema.sql").read_text(encoding="utf-8")
                    script = "\n".join(
                        line for line in schema.splitlines()
                        if not line.lstrip().startswith("--")
                    )
                    for statement in script.split(";"):
                        if statement.strip():
                            cursor.execute(statement)
            connection.commit()
        finally:
            connection.close()

    def setUp(self):
        self.connection = mysql.connector.connect(**self.options)
        with self.connection.cursor() as cursor:
            cursor.execute("INSERT INTO Adres (adres) VALUES ('Teststraat 13')")
            address_id = cursor.lastrowid
            self.address_id = address_id
            cursor.execute(
                "INSERT INTO Leverancier (naam, adres_id, contactpersoon, telefoonnummer) "
                "VALUES (%s, %s, 'Testcontact', '0123456789')",
                (f"Fabrikant-{uuid4().hex[:8]}", address_id),
            )
            self.supplier_id = cursor.lastrowid
        self.connection.commit()
        self.repository = ProductRepository(self.connection)
        self.service = ProductService(
            self.repository, SupplierRepository(self.connection)
        )

    def tearDown(self):
        self.connection.close()

    def form(self):
        suffix = uuid4().hex[:10]
        return {
            "article_number": f"CASE-{suffix}",
            "order_code": f"ORDER-{suffix}",
            "product_name": f"Casusmedicijn {suffix}",
            "price_per_bulk_package": "24,50",
            "package_type": "doos",
            "number_of_retail_packages": "10",
            "short_description": "Korte omschrijving",
            "long_description": "Lange omschrijving voor de catalogus",
            "minimum_order_quantity": "2",
            "minimum_stock": "15",
            "ingredient_name": ["Stof A", "Stof B"],
            "ingredient_quantity": ["10 mg", "20 mg"],
            "supplier_id": str(self.supplier_id),
            "purchase_price": "18,75",
        }

    def test_create_update_remove_keeps_purchase_history(self):
        data = self.form()
        product_id = self.service.add_product(data)
        initial = self.service.get_product(product_id)
        self.assertEqual(len(initial.active_ingredients), 2)
        self.assertEqual(initial.long_description, data["long_description"])
        purchase_id = PurchaseOrderRepository(self.connection).create(
            self.supplier_id, product_id, 2
        )
        edited = {**data, "price_per_bulk_package": "25,95"}
        edited["ingredient_name"] = ["Stof A", "Stof C", "Stof D"]
        edited["ingredient_quantity"] = ["10 mg", "30 mg", "40 mg"]
        self.service.update_product(product_id, edited)
        self.assertEqual(len(self.service.get_product(product_id).active_ingredients), 3)
        self.assertEqual(self.service.get_product(product_id).price_per_bulk_package, read_product(edited).price_per_bulk_package)

        self.assertIn(product_id, [
            row["product_id"] for row in SalesStockRepository(self.connection).find_products(data["article_number"])
        ])
        self.assertIn(product_id, [
            row["product_id"] for row in StockRepository(self.connection).list_stock_below_minimum()
        ])
        self.assertTrue(SupplierRepository(self.connection).find_offers(data["product_name"]))

        self.service.remove_from_assortment(product_id)
        with self.assertRaises(NotFoundError):
            self.service.get_product(product_id)
        self.assertNotIn(product_id, [
            row["product_id"] for row in SalesStockRepository(self.connection).find_products(data["article_number"])
        ])
        self.assertNotIn(product_id, [
            row["product_id"] for row in StockRepository(self.connection).list_stock_below_minimum()
        ])
        self.assertFalse(SupplierRepository(self.connection).find_offers(data["product_name"]))
        with self.assertRaises(DomainError):
            PurchaseOrderRepository(self.connection).create(self.supplier_id, product_id, 2)
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT in_assortiment FROM Product WHERE product_id=%s", (product_id,))
            self.assertEqual(cursor.fetchone(), (0,))
            cursor.execute("SELECT COUNT(*) FROM ProductWerkzameStof WHERE product_id=%s", (product_id,))
            self.assertEqual(cursor.fetchone()[0], 3)
            cursor.execute("SELECT COUNT(*) FROM LeveranciersAanbod WHERE product_id=%s", (product_id,))
            self.assertEqual(cursor.fetchone()[0], 1)
            cursor.execute("SELECT COUNT(*) FROM Inkoopbestelregel WHERE inkoopbestelling_id=%s AND product_id=%s", (purchase_id, product_id))
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_internal_reorder_removal_is_not_assortment_removal(self):
        product_id = self.service.add_product(self.form())
        SupplierRepository(self.connection).remove_from_internal_reorder_list(product_id)
        self.assertIsNotNone(self.service.get_product(product_id))
        self.assertNotEqual(self.service.catalog(), [])
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT in_assortiment, intern_bestelbaar FROM Product WHERE product_id=%s", (product_id,))
            self.assertEqual(cursor.fetchone(), (1, 0))
        with self.assertRaises(DomainError):
            PurchaseOrderRepository(self.connection).create(self.supplier_id, product_id, 2)

    def test_duplicate_code_rejected_by_database_and_rolled_back(self):
        data = self.form()
        self.service.add_product(data)
        product = read_product(data)
        with self.assertRaises(ConflictError):
            self.repository.add(product, SupplierOffer(self.supplier_id, product.price_per_bulk_package))
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Product WHERE artikelnummer=%s", (data["article_number"],))
            self.assertEqual(cursor.fetchone()[0], 1)

    def test_duplicate_ingredient_under_mysql_collation_is_a_conflict(self):
        data = self.form()
        data["ingredient_name"] = ["Cafeine", "Caféine"]
        with self.assertRaises(ConflictError):
            self.service.add_product(data)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM Product WHERE artikelnummer=%s",
                (data["article_number"],),
            )
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_supplier_fk_failure_rolls_back_product_creation(self):
        data = self.form()
        product = read_product(data)
        with self.assertRaises(mysql.connector.IntegrityError):
            self.repository.add(product, SupplierOffer(2147483647, product.price_per_bulk_package))
        with self.connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM Product WHERE artikelnummer=%s", (data["article_number"],))
            self.assertEqual(cursor.fetchone()[0], 0)

    def test_existing_customer_orders_deliveries_and_invoices_survive_removal(self):
        data = self.form()
        product_id = self.service.add_product(data)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO Klant (bedrijfsnaam, afleveradres_id, betaaladres_id) "
                "VALUES ('Testapotheek', %s, %s)",
                (self.address_id, self.address_id),
            )
            customer_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Bestelling (klant_id, afleveradres_id, betaaladres_id, "
                "besteld_op, gewenste_leverdatum, dagdeel, status_naam) "
                "VALUES (%s, %s, %s, '2026-11-01 09:00:00', '2026-11-02', "
                "'ochtend', 'verstuurd')",
                (customer_id, self.address_id, self.address_id),
            )
            order_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Bestelregel "
                "(bestelling_id, product_id, aantal, prijs_per_eenheid) "
                "VALUES (%s, %s, 2, 24.50)", (order_id, product_id)
            )
            cursor.execute(
                "INSERT INTO Levering (bestelling_id) VALUES (%s)", (order_id,)
            )
            delivery_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Factuur (klant_id, factuurdatum) "
                "VALUES (%s, '2026-11-03')", (customer_id,)
            )
            invoice_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO Leveringregel (levering_id, product_id, aantal_geleverd, factuur_id) "
                "VALUES (%s, %s, 2, %s)", (delivery_id, product_id, invoice_id)
            )
        self.connection.commit()

        self.service.remove_from_assortment(product_id)
        with self.connection.cursor() as cursor:
            cursor.execute(
                "SELECT b.aantal, b.prijs_per_eenheid, l.aantal_geleverd, l.factuur_id "
                "FROM Bestelregel AS b "
                "JOIN Leveringregel AS l ON l.product_id = b.product_id "
                "WHERE b.bestelling_id = %s AND b.product_id = %s",
                (order_id, product_id),
            )
            quantity, unit_price, delivered, saved_invoice = cursor.fetchone()
        self.assertEqual(quantity, 2)
        self.assertEqual(str(unit_price), "24.50")
        self.assertEqual(delivered, 2)
        self.assertEqual(saved_invoice, invoice_id)
