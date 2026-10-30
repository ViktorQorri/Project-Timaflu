"""Five required backend scenarios from the Timaflu product description.

School permits example data for methods. Database persistence is separate.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange


def eur(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_discount(subtotal, previous_annual_revenue, first_order=False):
    total = eur(subtotal)
    annual = eur(previous_annual_revenue)
    if min(total, annual) < 0:
        raise ValueError("Negative amount")
    order = eur(total * Decimal("0.05")) if total >= 500 else eur(0)
    total -= order
    welcome = eur(total * Decimal("0.10")) if first_order else eur(0)
    total -= welcome
    rate = Decimal("0.05") if annual < 10000 else Decimal("0.10") if annual < 20000 else Decimal("0.15")
    customer = eur(total * rate)
    return {"order_discount": order, "welcome_discount": welcome,
            "customer_discount": customer, "total": eur(total - customer)}


def cheapest_suppliers(product_name, offers):
    """Only matching product; include prices and contact details."""
    return sorted((o for o in offers if o["product"].casefold() == product_name.casefold()),
                  key=lambda o: (eur(o["price"]), o["supplier"]))


def outstanding_invoices(customer_id, invoices, today):
    """First and second reminders; contact after three unpaid weeks."""
    result = []
    for invoice in invoices:
        if invoice["customer_id"] != customer_id or invoice.get("paid"):
            continue
        days = (today - invoice["date"]).days
        action = ("contact_payment_plan" if days >= 21 else
                  "second_reminder" if days >= 14 else
                  "first_reminder" if days >= 7 else "no_action")
        result.append({**invoice, "action": action})
    return result


def second_delivery_attempt(deliveries, delivery_date, order_id, result=None):
    """One more delivery attempt on the same day; track actual outcome."""
    entries = [dict(x) for x in deliveries if x["date"] == delivery_date]
    for delivery in entries:
        if delivery["order_id"] == order_id:
            delivery["first_attempt"] = "absent"
            delivery["second_attempt"] = result or "scheduled"
            return entries
    raise ValueError("Delivery not found")


def follow_up_prospects(visits, customers_with_orders, today):
    """One calendar month after visit, if no order, offer 10% with account."""
    month = today.month - 1 or 12
    year = today.year - (today.month == 1)
    cutoff = date(year, month, min(today.day, monthrange(year, month)[1]))
    return [{**v, "offer": "10% first order if account is created"}
            for v in visits if v["date"] <= cutoff
            and v["prospect_id"] not in customers_with_orders]
