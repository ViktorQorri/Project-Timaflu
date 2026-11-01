"""Avoid multiple conflicting Product domain classes across backend scenarios."""
import unittest
from domain import business
from domain.product import Product

class ProductClassConsistencyTests(unittest.TestCase):
    def test_single_canonical_product_and_dkd_methods(self):
        self.assertNotIn("Product", vars(business))
        for method in (
            "checkStock", "checkMinimumStock", "findSuppliersByPrice",
            "removeSupplier", "removeFromAssortment",
        ):
            self.assertTrue(callable(getattr(Product,method,None)), method)
