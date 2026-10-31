"""Group customer orders by status for management."""

from datetime import date

from domain.errors import DomainError

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

    def report(self, date_from, date_to):
        """Return orders split into open, backorder and delivered groups."""
        date_from = self._parse_date(date_from, "Vanaf")
        date_to = self._parse_date(date_to, "Tot en met")
        if date_from and date_to and date_from > date_to:
            raise DomainError("De begindatum moet op of voor de einddatum liggen.")

        orders = {key: [] for key, _ in GROUPS}
        for order in self.repository.list_orders(date_from, date_to):
            orders[self._group(order["status_naam"])].append(order)
        return {
            "date_from": date_from,
            "date_to": date_to,
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

    @staticmethod
    def _parse_date(value, label):
        value = (value or "").strip()
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise DomainError(
                f"{label}: vul een geldige datum in (jjjj-mm-dd)."
            ) from error
