from datetime import date
from decimal import Decimal, InvalidOperation

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.business import Invoice
from domain.errors import ConflictError, DomainError, ValidationError
from repositories.assessed_repository import AssessedRepository
from repositories.customer_repository import CustomerRepository
from repositories.discount_repository import DiscountRepository
from repositories.order_repository import OrderRepository
from repositories.order_status_notification_repository import OrderStatusNotificationRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.customer_service import CustomerService
from services.discount_service import DiscountService
from services.order_service import PARTS_OF_DAY, OrderService
from services.order_status_notification_service import OrderStatusNotificationService
from services.sales_stock_service import SalesStockService


sales = Blueprint("sales", __name__)

ORDER_LINE_ROWS = 3
MAX_ORDER_LINE_ROWS = 20


def customer_service():
    return CustomerService(CustomerRepository(get_connection()))


def render_customers(form=None, errors=(), status=200):
    """Render the customer overview with the form for a new customer."""
    search = request.args.get("q", "", type=str).strip()
    year = date.today().year - 1
    rows = customer_service().overview(search, year)
    return render_template(
        "customers.html",
        customers=rows,
        search=search,
        year=year,
        discount_year=year + 1,
        form=form or {},
        errors=errors,
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
    return render_template(
        "customer_edit.html", customer_id=customer_id, form=customer, errors=()
    )


@sales.post("/customers/<int:customer_id>/edit")
def update_customer(customer_id):
    """Save the changed customer data, or show the form again with the validation errors."""
    try:
        customer_service().update(customer_id, request.form)
    except ValidationError as error:
        return render_template(
            "customer_edit.html",
            customer_id=customer_id,
            form=request.form,
            errors=error.messages,
        ), 400
    flash(f"De gegevens van klant {customer_id} zijn opgeslagen.", "success")
    return redirect(url_for("sales.customers"))


@sales.get("/customers/<int:customer_id>/deactivate")
def confirm_deactivate_customer(customer_id):
    """Ask confirmation before deactivating, preserving order and invoice history."""
    return render_template(
        "customer_deactivate.html", customer=customer_service().get(customer_id)
    )


@sales.post("/customers/<int:customer_id>/deactivate")
def deactivate_customer(customer_id):
    """Deactivate a customer while retaining all linked business records."""
    customer_service().deactivate(customer_id)
    flash(f"Klant {customer_id} is gedeactiveerd.", "success")
    return redirect(url_for("sales.customers"))


@sales.get("/orders")
def orders():
    """Show order availability based on physical and reserved stock."""
    query = request.args.get("q", "", type=str).strip()
    quantity = request.args.get("quantity", "1", type=str)
    order_search = request.args.get("order", "", type=str).strip()
    products = (
        SalesStockService(SalesStockRepository(get_connection())).check(query, quantity)
        if query
        else []
    )
    found_orders = (
        OrderStatusNotificationService(
            OrderStatusNotificationRepository(get_connection())
        ).search(order_search)
        if order_search
        else []
    )
    return render_template(
        "orders.html",
        query=query,
        quantity=quantity,
        products=products,
        order_search=order_search,
        found_orders=found_orders,
    )


@sales.get("/orders/<int:order_id>/status")
def order_status(order_id):
    """Show order status and a message employees can share with the customer."""
    service = OrderStatusNotificationService(
        OrderStatusNotificationRepository(get_connection())
    )
    return render_template(
        "order_status_notification.html",
        **service.status_overview(order_id),
    )


@sales.post("/orders/calculate-discount")
def calculate_order_discount():
    """Calculate discounts using the customer's recorded revenue and order history."""
    try:
        customer_id = int(request.form["customer_id"])
        subtotal = Decimal(request.form["subtotal"])
    except (TypeError, ValueError, KeyError, InvalidOperation) as error:
        raise DomainError("Vul een geldig klantnummer en bestelbedrag in.") from error
    if not subtotal.is_finite() or subtotal < 0:
        raise DomainError("Vul een geldig, niet-negatief bestelbedrag in.")
    if customer_id <= 0:
        raise DomainError("Klantnummer moet positief zijn.")
    repository = AssessedRepository(get_connection())
    customer, revenue = repository.customer_revenue(customer_id, date.today().year - 1)
    first_order = repository.customer_order_count(customer_id) == 0
    try:
        result = Invoice(customer_id, "preview", date.today()).createWeeklyInvoice(
            customer["bedrijfsnaam"],
            "",
            [{"quantity": 1, "unit_price": subtotal}],
            revenue,
            first_order,
        )
    except ValueError as error:
        raise DomainError("Vul een geldig, niet-negatief bestelbedrag in.") from error
    return render_template(
        "discount.html",
        customer=customer,
        annual_revenue=revenue,
        first_order=first_order,
        discount=result,
    )


@sales.get("/orders/new")
def new_order():
    """Enter a telephone order with stock checks and calculated discounts."""
    service = _order_service()
    form = _order_form(request.args)
    calculation, error, status = None, None, 200
    if not form["edit_lines"] and (
        form["customer_id"] or any(product_id for product_id, _ in form["lines"])
    ):
        try:
            calculation = service.prepare(
                form["customer_id"], form["lines"], form["backorders"]
            )
        except DomainError as domain_error:
            error, status = str(domain_error), domain_error.status_code
    return _render_order(service, form, calculation, error), status


@sales.post("/orders/new")
def place_order():
    """Save the order the customer agreed to, with its lines and reservations."""
    service = _order_service()
    form = _order_form(request.form)
    try:
        if not form["customer_approved"]:
            raise DomainError("Vraag de klant om akkoord op het totaalbedrag voordat je de bestelling opslaat.")
        saved = service.place(
            form["customer_id"],
            form["lines"],
            form["backorders"],
            form["delivery_date"],
            form["part_of_day"],
            form["urgent"],
        )
    except DomainError as domain_error:
        try:
            calculation = service.prepare(
                form["customer_id"], form["lines"], form["backorders"]
            )
        except DomainError:
            calculation = None
        return _render_order(service, form, calculation, str(domain_error)), domain_error.status_code
    message = (
        f"Order {saved['order_id']} is opgeslagen. Levering op "
        f"{saved['delivery_date']:%d-%m-%Y} in de {saved['part_of_day']}."
    )
    if saved["backorders"]:
        message += " Regels zonder voorraad staan als backorder."
    flash(message, "success")
    return redirect(url_for("sales.new_order"))


def _order_service():
    connection = get_connection()
    return OrderService(
        OrderRepository(connection),
        DiscountService(DiscountRepository(connection)),
    )


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
        "customer_approved": values.get("customer_approved") == "yes",
        "add_line": values.get("add_line") == "1",
        "edit_lines": values.get("add_line") == "1" or remove_line is not None,
    }


def _render_order(service, form, calculation, error):
    line_rows = min(
        max(ORDER_LINE_ROWS, len(form["lines"]) + form["add_line"]),
        MAX_ORDER_LINE_ROWS,
    )
    return render_template(
        "order_new.html",
        form=form,
        calculation=calculation,
        error=error,
        line_rows=line_rows,
        max_line_rows=MAX_ORDER_LINE_ROWS,
        parts_of_day=PARTS_OF_DAY,
        today=date.today().isoformat(),
        **service.discount_service.form_options(),
    )
