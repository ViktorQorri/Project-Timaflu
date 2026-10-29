"""Case-scoped stock check for telephone sales."""

from domain.errors import DomainError

class SalesStockService:
    def __init__(self, repository):
        self.repository = repository

    def check(self, query, quantity):
        query = (query or "").strip()
        if not query:
            return []
        try:
            quantity = int(quantity)
        except (TypeError, ValueError) as error:
            raise DomainError("Requested quantity must be a positive whole number.") from error
        if quantity < 1:
            raise DomainError("Requested quantity must be a positive whole number.")
        rows = self.repository.find_products(query)
        return [
            {**item, "voldoende": item["voorraad"] >= quantity}
            for item in rows
        ]
