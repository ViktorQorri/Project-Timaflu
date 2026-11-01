from datetime import date
from decimal import Decimal, InvalidOperation
from uuid import uuid4
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import current_app, session


from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.errors import DomainError, ValidationError
from domain.business import Order, euro
from repositories.discount_repository import DiscountRepository
from repositories.customer_repository import CustomerRepository
from repositories.sales_stock_repository import SalesStockRepository
from repositories.sales_case_repository import SalesCaseRepository
from repositories.telephone_order_repository import TelephoneOrderRepository
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

@sales.get("/orders/status")
def order_status():
    raw = request.args.get("customer_id", "").strip()
    if raw:
        try:
            customer_id = int(raw)
        except ValueError as exc:
            raise DomainError("Voer een geldig klantnummer in.") from exc
        if customer_id < 1:
            raise DomainError("Klantnummer moet positief zijn.")
    else:
        customer_id = None
    rows = SalesCaseRepository(get_connection()).order_statuses(customer_id)
    return render_template("order_status.html", orders=rows, customer_id=raw)


@sales.get("/orders")
def orders():
    """Show the orders page."""
    query = request.args.get("q", "", type=str).strip()
    quantity = request.args.get("quantity", "1", type=str)
    products = SalesStockService(SalesStockRepository(get_connection())).check(query, quantity) if query else []
    return render_template("orders.html", query=query, quantity=quantity, products=products)


@sales.post("/orders/calculate-discount")
def calculate_order_discount():
    try:
        customer_id=int(request.form["customer_id"])
        subtotal=request.form["subtotal"]
    except (TypeError,ValueError,KeyError) as exc:
        raise DomainError("Klantnummer en ordertotaal zijn verplicht.") from exc
    if customer_id<=0:
        raise DomainError("Klantnummer moet positief zijn.")
    repository = DiscountRepository(get_connection())
    customer = repository.find_customer(customer_id)
    if customer is None:
        raise DomainError("Deze klant bestaat niet of is niet actief.")
    first_order = repository.count_previous_orders(customer_id) == 0
    year = date.today().year
    rate = repository.get_customer_discount_percentage(customer_id, year)
    if rate is None:
        if not first_order:
            raise DomainError(f"De klantenkorting voor {year} is niet vastgelegd.")
        rate = Decimal("5")
    try:
        subtotal_ex = euro(subtotal)
        vat = euro(subtotal_ex * Decimal("0.09"))
        gross = subtotal_ex + vat
        result = Order(
            gross, 0, first_order, customerDiscountPercentage=rate
        ).calculateTotalAmount()
    except (ValueError, InvalidOperation) as exc:
        raise DomainError("Vul een geldig, niet-negatief orderbedrag in.") from exc
    return render_template(
        "discount.html", customer=customer,
        subtotal_ex= subtotal_ex, vat=vat, gross=gross,
        discount_year=year, customer_discount_percentage=rate,
        first_order=first_order, discount=result
    )


def _approval_serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="timaflu-telefonisch-orderakkoord")


@sales.get("/orders/new")
def new_telephone_order():
    customers, products = TelephoneOrderRepository(get_connection()).form_options()
    entered = request.args.getlist("product_id")
    line_rows = max(6, len(entered) + (request.args.get("add_line") == "1"))
    return render_template(
        "telephone_order.html", customers=customers, products=products,
        today=date.today().isoformat(), line_rows=line_rows,
        entered={
            "customer_id": request.args.get("customer_id", ""),
            "day": request.args.get("day", ""),
            "slot": request.args.get("slot", "ochtend"),
            "urgent": request.args.get("urgent") == "yes",
            "products": entered,
            "quantities": request.args.getlist("quantity"),
            "shortages": request.args.getlist("shortage"),
        },
    )


@sales.post("/orders/quote")
def preview_telephone_order():
    """Show exactly the order amount to be approved verbally by the customer."""
    try:
        wanted = [
            {"product_id": pid, "quantity": qty, "shortage": choice}
            for pid, qty, choice in zip(
                request.form.getlist("product_id"), request.form.getlist("quantity"),
                request.form.getlist("shortage"), strict=True)
            if pid.strip() or qty.strip()
        ]
        day = date.fromisoformat(request.form["day"])
    except (ValueError, KeyError) as exc:
        raise DomainError("Vul een geldige leverdag en complete bestelregels in.") from exc
    urgent = request.form.get("urgent") == "yes"
    customer_id = request.form.get("customer_id")
    slot = request.form.get("slot")
    quote = TelephoneOrderRepository(get_connection()).quote(
        customer_id, wanted, day, slot, urgent
    )
    nonce = uuid4().hex
    session["telephone_quote_nonce"] = nonce
    payload = {
        "nonce": nonce, "customer_id": quote["customer_id"],
        "wanted": wanted, "day": day.isoformat(), "slot": slot,
        "urgent": urgent, "fingerprint": quote["fingerprint"]
    }
    return render_template("telephone_order_quote.html", quote=quote,
                           quote_token=_approval_serializer().dumps(payload))


@sales.post("/orders/confirm")
def confirm_telephone_order():
    """No recorded order or reservation without a confirmed and unchanged quote."""
    if request.form.get("customer_approved") != "yes":
        raise DomainError("Leg eerst het definitieve akkoord van de klant vast.")
    try:
        payload = _approval_serializer().loads(request.form["quote_token"], max_age=900)
        day = date.fromisoformat(payload["day"])
    except (SignatureExpired, BadSignature, KeyError, ValueError, TypeError) as exc:
        raise DomainError("De prijsbevestiging is verlopen of ongeldig. Bereken de order opnieuw.") from exc
    if not payload["nonce"] or session.get("telephone_quote_nonce") != payload["nonce"]:
        raise DomainError("Deze prijsbevestiging is al gebruikt of hoort niet bij dit gesprek.")
    result = TelephoneOrderRepository(get_connection()).approve(
        payload["customer_id"], payload["wanted"], day, payload["slot"],
        payload["urgent"], payload["fingerprint"]
    )
    session.pop("telephone_quote_nonce", None)
    flash("Bestelling na akkoord vastgelegd en beschikbare voorraad voor robots gereserveerd.", "success")
    return redirect(url_for("sales.order_status", customer_id=payload["customer_id"]))
