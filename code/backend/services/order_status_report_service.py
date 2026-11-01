"""Group existing orders by their stored order status for reporting."""

BACKORDER = "backorder"
DELIVERED = "afgeleverd"

GROUPS = (
    ("open", "Openstaande orders"),
    ("backorder", "Backorders"),
    ("delivered", "Afgeleverde orders"),
)


class OrderStatusReportService:
    def __init__(self, repository):
        self.repository = repository

    def report(self):
        """Show all orders, without inventing additional statuses or business rules."""
        orders = {key: [] for key, _ in GROUPS}
        for order in self.repository.list_orders():
            orders[self._group(order["status_naam"])].append(order)
        return {
            "total": sum(len(rows) for rows in orders.values()),
            "groups": [
                {"key": key, "label": label, "orders": orders[key]}
                for key, label in GROUPS
            ],
        }

    @staticmethod
    def _group(status):
        if status == BACKORDER:
            return "backorder"
        if status == DELIVERED:
            return "delivered"
        return "open"
