"""Validate purchasing-order inputs before writing to the database."""

from domain.errors import DomainError


class PurchaseOrderService:
    def __init__(self, repository):
        self.repository = repository

    def record_order(self, supplier_id, product_id, quantity, confirmed):
        """Record only explicit purchasing-employee confirmed orders."""
        if confirmed != "yes":
            raise DomainError("Bevestig eerst dat je de fabrikant hebt gesproken.")
        try:
            supplier_id = int(supplier_id)
            product_id = int(product_id)
            quantity = int(quantity)
        except (ValueError, TypeError):
            raise DomainError("Leverancier, product en aantal moeten hele getallen zijn.")
        if min(supplier_id, product_id, quantity) <= 0:
            raise DomainError("Leverancier, product en aantal moeten groter dan 0 zijn.")
        return self.repository.create(supplier_id, product_id, quantity)

    def recorded_orders(self):
        """Return digitally recorded supplier orders for the purchasing overview."""
        return self.repository.list_recorded()
