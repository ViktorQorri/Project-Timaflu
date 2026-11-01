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
        lines = self.repository.find_order_lines(order_id)
        has_backorder = order.get("status_naam") == "backorder"

        # An accepted shortage is a recorded customer decision, not proof of
        # current stock shortage. Delivery, reservation and robot assignments
        # describe different steps and can overlap; never add their quantities
        # together to invent a missing-stock amount.
        progress_fields = (
            "gereserveerd", "in_open_deelorder", "in_afgeronde_deelorder",
            "in_open_levering", "aantal_afgeleverd",
        )
        detailed_lines = []
        for original in lines:
            line = dict(original)
            for field in progress_fields:
                line[field] = int(line.get(field) or 0)
            if line["aantal_afgeleverd"] > line["aantal"]:
                progress = "Afgeleverde hoeveelheid controleren"
            elif line["aantal_afgeleverd"] == line["aantal"]:
                progress = "Volledig afgeleverd"
            elif line["in_open_levering"]:
                progress = "Levering geregistreerd, ontvangst niet bevestigd"
            elif line["in_afgeronde_deelorder"]:
                progress = "Deelorder afgerond, aflevering niet bevestigd"
            elif line["in_open_deelorder"]:
                progress = "Deelorder aangemaakt, nog niet afgerond"
            elif line["gereserveerd"]:
                progress = "Voorraad voor deze bestelling gereserveerd"
            elif line["aantal_afgeleverd"]:
                progress = "Deels afgeleverd, geen vervolgstap geregistreerd"
            else:
                progress = "Geen reservering of verdere verwerking geregistreerd"
            detailed_lines.append({**line, "proces_label": progress})

        shortage_lines = [
            line for line in detailed_lines if line["afnemen_bij_tekort"] == 1
        ]
        undelivered_shortages = [
            line for line in shortage_lines
            if line["aantal_afgeleverd"] < line["aantal"]
        ]
        # A cancelled shortage (FALSE / 0) is not due for delivery. NULL
        # means there was no recorded shortage choice and the line remains due.
        due_lines = [
            line for line in detailed_lines if line["afnemen_bij_tekort"] != 0
        ]
        delivery_status_conflict = (
            order.get("status_naam") == "afgeleverd"
            and (
                not due_lines
                or any(
                    line["aantal_afgeleverd"] != line["aantal"]
                    for line in due_lines
                )
            )
        )
        return {
            "order": order,
            "lines": detailed_lines,
            "has_backorder": has_backorder,
            "shortage_lines": shortage_lines,
            "undelivered_shortages": undelivered_shortages,
            "delivery_status_conflict": delivery_status_conflict,
        }
