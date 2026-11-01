"""Case-based order status lookup for telephone sales."""

from domain.errors import DomainError, NotFoundError

STATUSES = {
    "wordt verzameld": ("Wordt verzameld", "info"),
    "verstuurd": ("Verstuurd", "info"),
    "backorder": ("Backorder", "warning"),
    "afgeleverd": ("Afgeleverd", "success"),
}
NO_STATUS = ("Niet geregistreerd", "neutral")
MAX_SEARCH_LENGTH = 100
MAX_DATABASE_ORDER_ID = 2_147_483_647  # Bestelling.bestelling_id is a signed MySQL INT.


def _with_status(order):
    name = order.get("status_naam")
    label, tone = STATUSES.get(name, (name, "neutral") if name else NO_STATUS)
    return {**order, "status_label": label, "status_tone": tone}


class OrderStatusNotificationService:
    def __init__(self, repository):
        self.repository = repository

    def search(self, term):
        """Return only recorded orders, or an empty result for an empty search."""
        term = (term or "").strip()
        if not term:
            return []
        if len(term) > MAX_SEARCH_LENGTH:
            raise DomainError("De zoekterm mag maximaal 100 tekens bevatten.")
        order_id = None
        if term.isascii() and term.isdecimal():
            candidate = int(term)
            if candidate <= MAX_DATABASE_ORDER_ID:
                order_id = candidate
        return [_with_status(row) for row in self.repository.search_orders(order_id, term)]

    def status_overview(self, order_id):
        """Return factual order status, delivery preference and shortage decisions."""
        if isinstance(order_id, bool) or isinstance(order_id, float):
            raise DomainError("Het ordernummer moet een positief geheel getal zijn.")
        try:
            order_id = int(order_id)
        except (TypeError, ValueError, OverflowError) as error:
            raise DomainError("Het ordernummer moet een positief geheel getal zijn.") from error
        if not (1 <= order_id <= MAX_DATABASE_ORDER_ID):
            raise DomainError("Het ordernummer moet een geldig positief geheel getal zijn.")
        order = self.repository.find_order(order_id)
        if order is None:
            raise NotFoundError(f"Order {order_id} is niet gevonden.")
        order = _with_status(order)
        return {
            "order": order,
            "lines": self.repository.find_order_lines(order_id),
            "has_backorder": order.get("status_naam") == "backorder",
        }
