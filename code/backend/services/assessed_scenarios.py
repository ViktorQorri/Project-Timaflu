"""Five required backend scenarios from the Timaflu product description.

School permits example data for methods. Database persistence is separate.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from calendar import monthrange
from domain.business import Order, Product, Invoice, Route, ProspectiveCustomer


def eur(value):
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_discount(subtotal, previous_annual_revenue, first_order=False):
    """Use the DKD Order methods instead of duplicating their business rules."""
    result = Order(subtotal, previous_annual_revenue, first_order).calculateTotalAmount()
    return {"order_discount": result["order_discount"],
            "welcome_discount": result["first_order_discount"],
            "customer_discount": result["customer_discount"],
            "total": result["total"]}


def cheapest_suppliers(product_name, offers):
    """Offer listing delegates to Product.findSuppliersByPrice()."""
    return Product(product_name, offers).findSuppliersByPrice()


def outstanding_invoices(customer_id, invoices, today):
    """Only unpaid invoices of the selected customer."""
    result = []
    for record in invoices:
        if record["customer_id"] != customer_id or record.get("paid"):
            continue
        invoice = Invoice(customer_id, record.get("invoice_number", ""),
                          record["date"], record.get("paid_on"))
        result.append({**record, "action": invoice.checkPaymentArrears(today)})
    return result


def second_delivery_attempt(deliveries, delivery_date, order_id, result=None):
    return Route(delivery_date, deliveries).adjustSchedule(order_id, result)


def follow_up_prospects(visits, customers_with_orders, today):
    result = []
    for visit in visits:
        prospect = ProspectiveCustomer(str(visit["prospect_id"]),
                                       visit["prospect_id"] in customers_with_orders)
        if prospect.checkFollowUpAfterOneMonth(visit["date"], today):
            result.append({**visit, "offer": "10% first order if account is created"})
    return result
