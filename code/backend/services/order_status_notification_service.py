"""Look up an order's status so the sales employee can inform the customer.

The customer message is only composed for the employee to read out or copy;
nothing is sent and nothing is written to the database.
"""

from domain.errors import DomainError, NotFoundError

# Statuses from the case (OrderStatus table): Dutch label and design-system tone.
STATUSES = {
    "wordt verzameld": ("Wordt verzameld", "info"),
    "verstuurd": ("Verstuurd", "info"),
    "backorder": ("Backorder", "warning"),
    "afgeleverd": ("Afgeleverd", "success"),
}
NO_STATUS = ("Nog geen status", "neutral")
MAX_SEARCH_LENGTH = 100


def _date(value):
    return value.strftime("%d-%m-%Y") if value else ""


def _with_status(order):
    name = order.get("status_naam")
    label, tone = STATUSES.get(name, (name.capitalize(), "info") if name else NO_STATUS)
    return {**order, "status_label": label, "status_tone": tone}


class OrderStatusNotificationService:
    def __init__(self, repository):
        self.repository = repository

    def search(self, term):
        """Return orders matching an order number or customer name, or [] for an empty search."""
        term = (term or "").strip()
        if not term:
            return []
        if len(term) > MAX_SEARCH_LENGTH:
            raise DomainError("De zoekterm mag maximaal 100 tekens bevatten.")
        order_id = int(term) if term.isdigit() else None
        return [_with_status(row) for row in self.repository.search_orders(order_id, term)]

    def status_overview(self, order_id):
        """Return the order, its lines with backorder quantities and the message for the customer."""
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
        # Lines without (enough) reserved stock are waiting for stock while the order is in backorder.
        in_backorder = order.get("status_naam") == "backorder"
        lines = [
            {**line, "backorder": max(line["aantal"] - line["gereserveerd"], 0) if in_backorder else 0}
            for line in self.repository.find_order_lines(order_id)
        ]
        backorder_lines = [line for line in lines if line["backorder"] > 0]
        return {
            "order": order,
            "lines": lines,
            "backorder_lines": backorder_lines,
            "message": self._message(order, backorder_lines),
        }

    @staticmethod
    def _message(order, backorder_lines):
        """Compose the Dutch status message the employee gives to the customer."""
        parts = [f"Beste {order.get('contactpersoon') or order['bedrijfsnaam']},", ""]
        if order.get("status_naam"):
            parts.append(
                f"Uw bestelling {order['bestelling_id']} van {_date(order['besteld_op'])} "
                f"heeft de status '{order['status_label'].lower()}'."
            )
        else:
            parts.append(
                f"Uw bestelling {order['bestelling_id']} van {_date(order['besteld_op'])} "
                "is ontvangen en wordt verwerkt."
            )
        if order.get("afgeleverd_op"):
            parts.append(f"De bestelling is afgeleverd op {_date(order['afgeleverd_op'])}.")
        else:
            parts.append(
                f"De geplande levering is op {_date(order['gewenste_leverdatum'])} "
                f"in de {order['dagdeel']}."
            )
        if backorder_lines:
            products = ", ".join(f"{line['backorder']}x {line['productnaam']}" for line in backorder_lines)
            parts.append(f"De volgende producten zijn in backorder: {products}. "
                         "Deze zijn nog niet op voorraad.")
        parts += ["", "Met vriendelijke groet,", "Timaflu"]
        return "\n".join(parts)
