"""Retrieve factual order status information for a telephone sales employee."""

from domain.errors import DomainError, NotFoundError

STATUSES = {
    "wordt verzameld": ("Wordt verzameld", "info"),
    "verstuurd": ("Verstuurd", "info"),
    "backorder": ("Backorder", "warning"),
    "afgeleverd": ("Afgeleverd", "success"),
}
NO_STATUS = ("Niet geregistreerd", "neutral")
MAX_SEARCH_LENGTH = 100


def _with_status(order):
    name = order.get("status_naam")
    label, tone = STATUSES.get(name, (name, "info") if name else NO_STATUS)
    return {**order, "status_label": label, "status_tone": tone}


class OrderStatusNotificationService:
    def __init__(self, repository):
        self.repository = repository

    def search(self, term):
        term = (term or "").strip()
        if not term:
            return []
        if len(term) > MAX_SEARCH_LENGTH:
            raise DomainError("De zoekterm mag maximaal 100 tekens bevatten.")
        order_id = int(term) if term.isdigit() else None
        return [_with_status(row) for row in self.repository.search_orders(order_id, term)]

    def status_overview(self, order_id):
        try:
            order_id = int(order_id)
        except (TypeError, ValueError) as error:
            raise DomainError("Het ordernummer moet een positief geheel getal zijn.") from error
        if order_id < 1:
            raise DomainError("Het ordernummer moet een positief geheel getal zijn.")
        order = self.repository.find_order(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} is niet gevonden.")
        order = _with_status(order)
        # Stock reservation is not proof of an outstanding backorder quantity.
        # Partial deliveries and shortage choices are stored separately.
        return {
            "order": order,
            "lines": self.repository.find_order_lines(order_id),
            "has_backorder": order.get("status_naam") == "backorder",
        }
