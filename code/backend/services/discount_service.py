"""Order discount calculation for telephone sales, following SD01 Calculate customer discount.

Business rules from the case (Current-processes, Tabel 1):
- 5% order discount over the order total when the total is EUR 500 or more;
- the next discount is calculated over the amount left after the order discount;
- first order of a customer: one-time 10% discount;
- existing customer: customer discount based on the previous year's annual revenue.
Every amount is rounded to cents (ROUND_HALF_UP) after each step.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from domain.errors import DomainError, NotFoundError

CENT = Decimal("0.01")
ORDER_DISCOUNT_THRESHOLD = Decimal("500.00")
ORDER_DISCOUNT_PERCENTAGE = Decimal("5")
ONE_TIME_DISCOUNT_PERCENTAGE = Decimal("10")
# Tabel 1: lowest annual revenue of each tier and its percentage, highest tier first.
CUSTOMER_DISCOUNT_TIERS = (
    (Decimal("20000.00"), Decimal("15")),
    (Decimal("10000.00"), Decimal("10")),
    (Decimal("0.00"), Decimal("5")),
)


def to_cents(amount):
    """Round an amount to whole cents, halves away from zero."""
    return Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)


class DiscountService:
    """The Order participant of SD01: calculates the total amount and the applied discounts."""

    def __init__(self, repository):
        self.repository = repository

    def form_options(self):
        """Return the customers and products the sales employee can choose from."""
        return {
            "customers": self.repository.list_customers(),
            "products": self.repository.list_products(),
        }

    def calculate_total_amount(self, customer_id, order_lines, order_date=None):
        """SD01 calculateTotalAmount(customer, orderLines).

        Args:
            customer_id: The id of the customer placing the order.
            order_lines: (product_id, quantity) pairs; pairs that are both empty are skipped.
            order_date: The date of the order, today by default. Its previous year sets the
                annual revenue used for the customer discount.

        Returns:
            A dict with the customer, the priced lines, the subtotal, the applied discounts
            in order, the total amount, and how the second discount was chosen.
        """
        customer = self._find_customer(customer_id)
        lines = self._price_order_lines(order_lines)
        subtotal = to_cents(sum(line["line_total"] for line in lines))
        discounts = []

        order_discount = self.calculate_order_discount(subtotal)
        if order_discount:
            discounts.append(order_discount)
        amount = discounts[-1]["total_after"] if discounts else subtotal

        previous_year = (order_date or date.today()).year - 1
        first_order = self.repository.count_previous_orders(customer["klant_id"]) == 0
        annual_revenue = None
        if first_order:
            discounts.append(self.calculate_one_time_discount(amount))
        else:
            annual_revenue = self.calculate_annual_revenue(customer["klant_id"], previous_year)
            percentage = self.determine_discount_percentage(annual_revenue)
            discounts.append(self.calculate_customer_discount(amount, percentage))

        return {
            "customer": customer,
            "lines": lines,
            "subtotal": subtotal,
            "discounts": discounts,
            "total_amount": self.calculate_total_after_discount(subtotal, discounts),
            "first_order": first_order,
            "previous_year": previous_year,
            "annual_revenue": annual_revenue,
        }

    def calculate_order_discount(self, subtotal):
        """Return the 5% order discount for a total of EUR 500 or more, otherwise None."""
        if subtotal < ORDER_DISCOUNT_THRESHOLD:
            return None
        return self._discount("order", subtotal, ORDER_DISCOUNT_PERCENTAGE)

    def calculate_one_time_discount(self, amount):
        """SD01 calculateOneTimeDiscount(10%) for the first order of a customer."""
        return self._discount("one_time", amount, ONE_TIME_DISCOUNT_PERCENTAGE)

    def calculate_annual_revenue(self, customer_id, year):
        """SD01 Customer.calculateAnnualRevenue(previousYear), via sumPurchases(previousYear)."""
        return to_cents(self.repository.sum_purchases(customer_id, year))

    @staticmethod
    def determine_discount_percentage(annual_revenue):
        """SD01 CustomerDiscount.determineDiscountPercentage(annualRevenue), using Tabel 1."""
        try:
            annual_revenue = Decimal(annual_revenue)
        except (TypeError, ValueError, InvalidOperation) as error:
            raise DomainError("Jaaromzet moet een bedrag zijn.") from error
        if not annual_revenue.is_finite() or annual_revenue < 0:
            raise DomainError("Jaaromzet kan niet negatief zijn.")
        for lowest_revenue, percentage in CUSTOMER_DISCOUNT_TIERS:
            if annual_revenue >= lowest_revenue:
                return percentage

    def calculate_customer_discount(self, amount, percentage):
        """SD01 calculateCustomerDiscount(): the customer discount over the remaining amount."""
        return self._discount("customer", amount, percentage)

    @staticmethod
    def calculate_total_after_discount(subtotal, discounts):
        """SD01 calculateTotalAfterDiscount(): the subtotal minus every applied discount."""
        return subtotal - sum((discount["amount"] for discount in discounts), Decimal("0.00"))

    @staticmethod
    def _discount(kind, amount, percentage):
        discount = to_cents(amount * percentage / Decimal(100))
        return {
            "kind": kind,
            "percentage": percentage,
            "base": amount,
            "amount": discount,
            "total_after": amount - discount,
        }

    def _find_customer(self, customer_id):
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError) as error:
            raise DomainError("Kies een klant.") from error
        if customer_id < 1:
            raise DomainError("Kies een klant.")
        customer = self.repository.find_customer(customer_id)
        if customer is None:
            raise NotFoundError("Deze klant bestaat niet.")
        return customer

    def _price_order_lines(self, order_lines):
        lines = []
        seen = set()
        for product_id, quantity in order_lines:
            product_id = "" if product_id is None else str(product_id).strip()
            quantity = "" if quantity is None else str(quantity).strip()
            if not product_id and not quantity:
                continue
            try:
                product_id, quantity = int(product_id), int(quantity)
            except (TypeError, ValueError) as error:
                raise DomainError("Kies per bestelregel een medicijn en een aantal.") from error
            if product_id < 1 or quantity < 1:
                raise DomainError("Het aantal moet een positief geheel getal zijn.")
            if product_id in seen:
                raise DomainError("Elk medicijn mag maar één keer in de bestelling staan.")
            seen.add(product_id)
            product = self.repository.find_product(product_id)
            if product is None:
                raise NotFoundError("Dit medicijn staat niet in de catalogus.")
            price = to_cents(product["prijs_per_grootverpakking"])
            lines.append({**product, "quantity": quantity, "line_total": to_cents(price * quantity)})
        if not lines:
            raise DomainError("Voeg minimaal één bestelregel toe.")
        return lines
