from datetime import date

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from itsdangerous import BadSignature, URLSafeSerializer

from db import get_connection
from services.order_service import PARTS_OF_DAY, OrderService
from services.discount_service import DiscountService
from repositories.order_repository import OrderRepository
from repositories.discount_repository import DiscountRepository
from domain.errors import DomainError, ValidationError
from domain.business import Order
from repositories.assessed_repository import AssessedRepository
from repositories.customer_repository import CustomerRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.customer_service import CustomerService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)

# AD05 starts with three provisional order rows, with no artificial maximum.
ORDER_LINE_ROWS = 3


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


@sales.get("/customers/<int:customer_id>/deactivate")
def confirm_deactivate_customer(customer_id):
    """Confirm the AD07 deactivation action."""
    return render_template("customer_deactivate.html", customer=customer_service().get(customer_id))


@sales.post("/customers/<int:customer_id>/deactivate")
def deactivate_customer(customer_id):
    """Deactivate a customer while retaining all linked business records."""
    customer_service().deactivate(customer_id)
    flash(f"Klant {customer_id} is gedeactiveerd.", "success")
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
        if not form["quote"]:
            raise DomainError(
                "Bereken eerst het totaal en vraag de klant akkoord voordat je de order opslaat."
            )
        try:
            approved_quote = _quote_serializer().loads(form["quote"])
        except BadSignature as error:
            raise DomainError("De berekende order is ongeldig. Bereken de order opnieuw.") from error
        saved = service.place(
            form["customer_id"], form["lines"], form["backorders"],
            form["delivery_date"], form["part_of_day"], form["urgent"],
            expected_quote=approved_quote,
        )
    except DomainError as domain_error:
        try:
            calculation = service.prepare(form["customer_id"], form["lines"], form["backorders"])
        except DomainError:
            calculation = None
        return _render_order(service, form, calculation, str(domain_error)), domain_error.status_code
    message = (f"Order {saved['order_id']} is opgeslagen. Levering op "
               f"{saved['delivery_date']:%d-%m-%Y} in de {saved['part_of_day']}.")
    if saved["backorders"]:
        message += " Status: backorder. Regels zonder voorraad staan als backorder."
    else:
        message += " Status: wordt verzameld."
    flash(message, "success")
    return redirect(url_for("sales.new_order"))


def _quote_serializer():
    return URLSafeSerializer(current_app.secret_key, salt="timaflu-approved-order-quote")


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
        "quote": values.get("quote", "", type=str),
        "add_line": values.get("add_line") == "1",
        "edit_lines": values.get("add_line") == "1" or remove_line is not None,
    }


def _render_order(service, form, calculation, error):
    line_rows = max(ORDER_LINE_ROWS, len(form["lines"]) + form["add_line"])
    quote_token = (_quote_serializer().dumps(service.quote_snapshot(calculation))
                   if calculation is not None else "")
    return render_template(
        "order_new.html", form=form, calculation=calculation, error=error,
        quote_token=quote_token, line_rows=line_rows,
        parts_of_day=PARTS_OF_DAY, today=date.today().isoformat(),
        **service.discount_service.form_options(),
    )
