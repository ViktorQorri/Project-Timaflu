"""Enter a telephone order, following AD05 Enter order.

The employee picks a customer and order lines. The system checks the stock of every line,
calculates the discounts and total (SD01, DiscountService) and, once the customer agrees
on a delivery moment, saves the order with its reservations.
"""
from datetime import date

from domain.errors import ConflictError, DomainError
from repositories.order_repository import BLOCKED_MESSAGE

PARTS_OF_DAY = ("ochtend", "middag")


class OrderService:
    def __init__(self, repository, discount_service):
        """
        Args:
            repository: An OrderRepository, or a fake one in tests.
            discount_service: The DiscountService that calculates the total amount (SD01).
        """
        self.repository = repository
        self.discount_service = discount_service

    def prepare(self, customer_id, order_lines, backorder_ids=()):
        """Check the customer and the stock per line, then calculate the total (AD05 up to "Show total").

        Args:
            customer_id: The id of the customer placing the order.
            order_lines: (product_id, quantity) pairs; pairs that are both empty are skipped.
            backorder_ids: Product ids of short lines the customer accepts as backorder.

        Returns:
            The SD01 calculation; every line also has available, short and backorder,
            and can_save tells whether every short line was accepted as backorder.
        """
        # AD05 checks the customer's order block before any discount calculation.
        customer = self.discount_service._find_customer(customer_id)
        if self.repository.is_customer_blocked(customer["klant_id"]):
            raise ConflictError(BLOCKED_MESSAGE)
        calculation = self.discount_service.calculate_total_amount(customer_id, order_lines)
        accepted = {str(product_id) for product_id in backorder_ids}
        for line in calculation["lines"]:
            line["available"] = self.repository.available_stock(line["product_id"])
            line["short"] = line["available"] < line["quantity"]
            line["backorder"] = line["short"] and str(line["product_id"]) in accepted
        calculation["can_save"] = all(not line["short"] or line["backorder"] for line in calculation["lines"])
        return calculation

    @staticmethod
    def quote_snapshot(calculation):
        """Canonical values approved by the customer before saving (AD05)."""
        return {
            "customer_id": calculation["customer"]["klant_id"],
            "lines": [
                {"product_id": line["product_id"],
                 "quantity": line["quantity"],
                 "price": str(line["prijs_per_grootverpakking"]),
                 "available": line["available"]}
                for line in calculation["lines"]
            ],
            "subtotal": str(calculation["subtotal"]),
            "vat_amount": str(calculation["vat_amount"]),
            "gross_total": str(calculation["gross_total"]),
            "total": str(calculation["total_amount"]),
            "first_order": calculation["first_order"],
            "discount_year": calculation["discount_year"],
            "customer_discount_percentage": str(calculation["customer_discount_percentage"]),
        }

    def place(self, customer_id, order_lines, backorder_ids, delivery_date,
              part_of_day, urgent, today=None, expected_quote=None):
        """Save the order the customer agreed to (AD05 from "Agree delivery date").

        Args:
            customer_id, order_lines, backorder_ids: As in prepare().
            delivery_date: The agreed date as YYYY-MM-DD.
            part_of_day: "ochtend" or "middag".
            urgent: True for an urgent order, which may be delivered today.
            today: The current date, today by default.
            expected_quote: The signed, previously shown calculation from AD05.

        Returns:
            A dict with order_id, first_order, backorders, the delivery moment and the total amount.
        """
        calculation = self.prepare(customer_id, order_lines, backorder_ids)
        if expected_quote is not None and self.quote_snapshot(calculation) != expected_quote:
            raise ConflictError(
                "De bestelregels, beschikbare voorraad, prijs of korting zijn veranderd. "
                "Bereken opnieuw en vraag de klant opnieuw akkoord."
            )
        short = [line["productnaam"] for line in calculation["lines"] if line["short"] and not line["backorder"]]
        if short:
            raise DomainError(
                f"Te weinig voorraad voor {', '.join(short)}. Verwijder de regel of noteer hem als backorder."
            )
        delivery_date = self._delivery_date(delivery_date, urgent, today or date.today())
        if part_of_day not in PARTS_OF_DAY:
            raise DomainError("Kies ochtend of middag als dagdeel.")
        saved = self.repository.save_order(
            calculation["customer"]["klant_id"],
            [{"product_id": line["product_id"], "productnaam": line["productnaam"],
              "quantity": line["quantity"], "backorder": line["backorder"],
              "expected_price": line["prijs_per_grootverpakking"],
              "expected_available": line["available"]} for line in calculation["lines"]],
            delivery_date, part_of_day, bool(urgent), calculation["first_order"],
            calculation["one_time_discount"], calculation["discount_year"],
            calculation["customer_discount_percentage"],
        )
        return {**saved, "delivery_date": delivery_date, "part_of_day": part_of_day,
                "total_amount": calculation["total_amount"]}

    @staticmethod
    def _delivery_date(value, urgent, today):
        """An order is delivered from tomorrow; only an urgent order can be delivered today."""
        try:
            delivery_date = date.fromisoformat((value or "").strip())
        except ValueError as error:
            raise DomainError("Kies een leverdatum.") from error
        if delivery_date < today:
            raise DomainError("De leverdatum ligt in het verleden.")
        if urgent and delivery_date != today:
            raise DomainError(
                "Een spoedbestelling wordt dezelfde dag binnen drie uur geleverd. Kies vandaag."
            )
        if delivery_date == today and not urgent:
            raise DomainError("Vandaag leveren kan alleen bij een spoedbestelling. Kies een datum vanaf morgen.")
        return delivery_date
