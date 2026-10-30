from datetime import date

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.errors import ConflictError, ValidationError
from repositories.customer_repository import CustomerRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.customer_service import CustomerService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)


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
