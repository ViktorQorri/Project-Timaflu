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
            raise DomainError("Het gevraagde aantal moet een heel getal groter dan 0 zijn.") from error
        if quantity < 1:
            raise DomainError("Het gevraagde aantal moet een heel getal groter dan 0 zijn.")
        rows = self.repository.find_products(query)
        return [
            {**item, "voldoende": item["beschikbaar"] >= quantity}
            for item in rows
        ]
