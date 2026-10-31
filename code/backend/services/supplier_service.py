"""Purchasing supplier lookup service."""

class SupplierService:
    def __init__(self, supplier_repository):
        self.supplier_repository = supplier_repository

    def products_matching_name(self, product_name):
        """Resolve a user-entered name to uniquely selectable catalog products."""
        if not product_name or not product_name.strip():
            return []
        return self.supplier_repository.search_products_by_name(product_name.strip())

    def offers_for_product(self, product_name="", product_id=None):
        """Resolve a product by id (preferred), or exact name when searched manually."""
        if product_id is not None:
            if not isinstance(product_id, int) or product_id < 1:
                return []
            return self.supplier_repository.find_offers(product_id=product_id)
        if not product_name or not product_name.strip():
            return []
        return self.supplier_repository.find_offers(product_name.strip())
