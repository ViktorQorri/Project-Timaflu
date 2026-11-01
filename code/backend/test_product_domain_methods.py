"""DKD Product methods must agree with the normalized Product model."""
from decimal import Decimal
from unittest import TestCase
from domain.product import Product, SupplierOffer

class ProductDomainMethodsTests(TestCase):
    def make_product(self):
        return Product(
            product_id=1, article_number="M-1", order_code="B-1",
            product_name="Testmedicijn", price_per_bulk_package=Decimal("20.00"),
            package_type="doos", number_of_retail_packages=1,
            short_description="", long_description="",
            minimum_order_quantity=1, minimum_stock=5,
        )

    def test_stock_checks_use_physical_and_reservations(self):
        p=self.make_product()
        self.assertTrue(p.checkStock(4,1,3))
        self.assertFalse(p.checkStock(4,2,3))
        self.assertTrue(p.checkMinimumStock(4))
        self.assertFalse(p.checkMinimumStock(5))

    def test_supplier_selection_and_removal_do_not_delete_product(self):
        p=self.make_product()
        p.supplier_offers=[
            SupplierOffer(3,Decimal("9.00")),
            SupplierOffer(1,Decimal("5.00")),
        ]
        self.assertEqual([x.supplier_id for x in p.findSuppliersByPrice()],[1,3])
        self.assertEqual(p.removeSupplier(3),1)
        self.assertEqual([x.supplier_id for x in p.supplier_offers],[1])
        self.assertTrue(p.in_assortment)
        p.removeFromAssortment()
        self.assertFalse(p.in_assortment)
