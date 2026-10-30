from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.errors import DomainError
from repositories.discount_repository import DiscountRepository
from repositories.order_repository import OrderRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.discount_service import DiscountService
from services.order_service import PARTS_OF_DAY, OrderService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)

# Number of order line rows on the order form; empty rows are ignored.
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


@sales.get("/orders/new")
def new_order():
    """Enter a telephone order (AD05): stock per line, discounts and total (SD01)."""
    service = _order_service()
    form = _order_form(request.args)
    calculation, error, status = None, None, 200
    if form["customer_id"] or any(product_id for product_id, _ in form["lines"]):
        try:
            calculation = service.prepare(form["customer_id"], form["lines"], form["backorders"])
        except DomainError as domain_error:
            error, status = str(domain_error), domain_error.status_code
    return _render_order(service, form, calculation, error), status


@sales.post("/orders/new")
def place_order():
    """Save the order the customer agreed to, with its lines and reservations.

    A rejected order shows the page again with the message and the input kept.
    """
    service = _order_service()
    form = _order_form(request.form)
    try:
        saved = service.place(form["customer_id"], form["lines"], form["backorders"],
                              form["delivery_date"], form["part_of_day"], form["urgent"])
    except DomainError as domain_error:
        try:
            calculation = service.prepare(form["customer_id"], form["lines"], form["backorders"])
        except DomainError:
            calculation = None
        return _render_order(service, form, calculation, str(domain_error)), domain_error.status_code
    message = (f"Order {saved['order_id']} is opgeslagen. Levering op "
               f"{saved['delivery_date']:%d-%m-%Y} in de {saved['part_of_day']}.")
    if saved["backorders"]:
        message += " Regels zonder voorraad staan als backorder."
    flash(message, "success")
    return redirect(url_for("sales.new_order"))


def _order_service():
    connection = get_connection()
    return OrderService(OrderRepository(connection), DiscountService(DiscountRepository(connection)))


def _order_form(values):
    return {
        "customer_id": values.get("customer_id", "", type=str).strip(),
        "lines": list(zip(values.getlist("product_id"), values.getlist("quantity"))),
        "backorders": values.getlist("backorder"),
        "delivery_date": values.get("delivery_date", "", type=str),
        "part_of_day": values.get("part_of_day", "", type=str),
        "urgent": values.get("urgent") == "1",
    }


def _render_order(service, form, calculation, error):
    return render_template(
        "order_new.html", form=form, calculation=calculation, error=error, line_rows=ORDER_LINE_ROWS,
        parts_of_day=PARTS_OF_DAY, today=date.today().isoformat(), **service.discount_service.form_options(),
    )
