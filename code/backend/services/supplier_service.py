"""Purchasing supplier lookup service."""

class SupplierService:
    def __init__(self, supplier_repository):
        self.supplier_repository = supplier_repository

    def offers_for_product(self, product_name):
        """Return suppliers by price, or an empty list for an empty search."""
        if not product_name or not product_name.strip():
            return []
        return self.supplier_repository.find_offers(product_name.strip())
