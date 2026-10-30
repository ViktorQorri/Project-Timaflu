from flask import Blueprint, render_template, request

from db import get_connection
from domain.errors import DomainError
from repositories.discount_repository import DiscountRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.discount_service import DiscountService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)

# Number of order line rows on the discount form; empty rows are ignored.
ORDER_LINE_ROWS = 5


@sales.get("/customers")
def customers():
    """Show the customers page."""
    return render_template("customers.html")


@sales.get("/orders")
def orders():
    """Show the orders page."""
    query = request.args.get("q", "", type=str).strip()
    quantity = request.args.get("quantity", "1", type=str)
    products = SalesStockService(SalesStockRepository(get_connection())).check(query, quantity) if query else []
    return render_template("orders.html", query=query, quantity=quantity, products=products)


@sales.get("/orders/discount")
def order_discount():
    """Show the discount calculation for a telephone order (SD01). Nothing is saved."""
    service = DiscountService(DiscountRepository(get_connection()))
    customer_id = request.args.get("customer_id", "", type=str).strip()
    product_ids = request.args.getlist("product_id")
    quantities = request.args.getlist("quantity")
    form = {"customer_id": customer_id, "lines": list(zip(product_ids, quantities))}
    calculation, error, status = None, None, 200
    if customer_id or any(product_ids) or any(quantities):
        try:
            calculation = service.calculate_total_amount(customer_id, form["lines"])
        except DomainError as domain_error:
            error, status = str(domain_error), domain_error.status_code
    return render_template(
        "order_discount.html", form=form, calculation=calculation, error=error,
        line_rows=ORDER_LINE_ROWS, **service.form_options(),
    ), status
