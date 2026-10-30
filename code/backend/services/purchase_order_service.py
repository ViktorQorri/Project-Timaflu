"""Validate purchasing-order inputs before writing to the database."""

from domain.errors import DomainError


class PurchaseOrderService:
    def __init__(self, repository):
        self.repository = repository

    def record_order(self, supplier_id, product_id, quantity):
        """Record only explicit purchasing-employee confirmed orders."""
        try:
            supplier_id = int(supplier_id)
            product_id = int(product_id)
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise DomainError("Supplier, product, and quantity must be valid integers.")
        if min(supplier_id, product_id, quantity) <= 0:
            raise DomainError("Supplier, product, and quantity must be positive.")
        return self.repository.create(supplier_id, product_id, quantity)
