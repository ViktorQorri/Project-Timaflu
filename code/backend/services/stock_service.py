"""Business logic for inventory alerts."""


class StockService:
    """Determine deficits using current physical warehouse inventory."""

    def __init__(self, stock_repository):
        self.stock_repository = stock_repository

    def shortages(self):
        """Return shortage rows including the number of units missing."""
        rows = self.stock_repository.list_stock_below_minimum()
        return [
            {
                **row,
                "tekort": row["minimumvoorraad"] - row["voorraad"],
            }
            for row in rows
        ]

    def minimums(self):
        """Return all configured minimums with actual warehouse inventory."""
        return self.stock_repository.list_all_minimums()

    def set_minimum(self, product_id, value):
        """Use non-negative integral thresholds; zero disables shortage alerts."""
        from domain.errors import DomainError
        try:
            product_id = int(product_id)
            number = int(value)
        except (ValueError, TypeError):
            raise DomainError("Product en minimumvoorraad moeten hele getallen zijn.")
        if product_id < 1 or number < 0:
            raise DomainError("Minimumvoorraad mag niet negatief zijn.")
        # Reject noncanonical values like 2.5 or 3e2, not silently truncate.
        if str(value).strip() != str(number):
            raise DomainError("Minimumvoorraad moet een geheel getal zijn.")
        self.stock_repository.set_minimum(product_id, number)
