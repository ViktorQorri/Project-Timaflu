from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.errors import ConflictError, DomainError, ValidationError
from repositories.customer_repository import CustomerRepository
from repositories.discount_repository import DiscountRepository
from repositories.order_repository import OrderRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.customer_service import CustomerService
from services.discount_service import DiscountService
from services.order_service import PARTS_OF_DAY, OrderService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)

# Order line rows on the order form: three to start with, one more per "Medicijn toevoegen",
# one less per "Verwijderen" but never fewer than three. Empty rows are ignored.
ORDER_LINE_ROWS = 3
MAX_ORDER_LINE_ROWS = 20


def customer_service():
    return CustomerService(CustomerRepository(get_connection()))


def render_customers(form=None, errors=(), status=200):
    """Render the customer overview with the form for a new customer."""
    search = request.args.get("q", "", type=str).strip()
    year = date.today().year
    rows = customer_service().overview(search, year)
    return render_template(
        "customers.html", customers=rows, search=search, year=year,
        form=form or {}, errors=errors,
    ), status


@sales.get("/customers")
def customers():
    """Show the customers page."""
    return render_customers()


@sales.post("/customers")
def create_customer():
    """Save a new customer, or show the form again with the validation errors."""
    try:
        customer_id = customer_service().create(request.form)
    except ValidationError as error:
        return render_customers(request.form, error.messages, 400)
    flash(f"Klant {customer_id} is aangemaakt.", "success")
    return redirect(url_for("sales.customers"))


@sales.get("/customers/<int:customer_id>/edit")
def edit_customer(customer_id):
    """Show the form with the current data of one customer."""
    customer = customer_service().get(customer_id)
    return render_template("customer_edit.html", customer_id=customer_id, form=customer, errors=())


@sales.post("/customers/<int:customer_id>/edit")
def update_customer(customer_id):
    """Save the changed customer data, or show the form again with the validation errors."""
    try:
        customer_service().update(customer_id, request.form)
    except ValidationError as error:
        return render_template(
            "customer_edit.html", customer_id=customer_id, form=request.form, errors=error.messages,
        ), 400
    flash(f"De gegevens van klant {customer_id} zijn opgeslagen.", "success")
    return redirect(url_for("sales.customers"))


@sales.get("/customers/<int:customer_id>/delete")
def confirm_delete_customer(customer_id):
    """Ask the employee to confirm deleting a customer."""
    return render_template("customer_delete.html", customer=customer_service().get(customer_id))


@sales.post("/customers/<int:customer_id>/delete")
def delete_customer(customer_id):
    """Delete a confirmed customer, or explain why it cannot be deleted."""
    try:
        customer_service().delete(customer_id)
    except ConflictError as error:
        flash(str(error), "error")
        return redirect(url_for("sales.customers"))
    flash(f"Klant {customer_id} is verwijderd.", "success")
    return redirect(url_for("sales.customers"))


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
    # Adding or removing a row only shows the form again; "Totaal berekenen" calculates the total.
    if not form["edit_lines"] and (form["customer_id"] or any(product_id for product_id, _ in form["lines"])):
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
    lines = list(zip(values.getlist("product_id"), values.getlist("quantity")))
    remove_line = values.get("remove_line", type=int)
    if remove_line is not None and 0 <= remove_line < len(lines):
        del lines[remove_line]
    return {
        "customer_id": values.get("customer_id", "", type=str).strip(),
        "lines": lines,
        "backorders": values.getlist("backorder"),
        "delivery_date": values.get("delivery_date", "", type=str),
        "part_of_day": values.get("part_of_day", "", type=str),
        "urgent": values.get("urgent") == "1",
        "add_line": values.get("add_line") == "1",
        "edit_lines": values.get("add_line") == "1" or remove_line is not None,
    }


def _render_order(service, form, calculation, error):
    line_rows = min(max(ORDER_LINE_ROWS, len(form["lines"]) + form["add_line"]), MAX_ORDER_LINE_ROWS)
    return render_template(
        "order_new.html", form=form, calculation=calculation, error=error, line_rows=line_rows,
        max_line_rows=MAX_ORDER_LINE_ROWS, parts_of_day=PARTS_OF_DAY, today=date.today().isoformat(),
        **service.discount_service.form_options(),
    )
