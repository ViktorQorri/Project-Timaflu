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
