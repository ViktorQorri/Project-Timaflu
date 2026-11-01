from datetime import date
from decimal import InvalidOperation
from uuid import uuid4
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from flask import Blueprint, render_template, request, current_app, session, redirect, url_for, flash
from db import get_connection
from repositories.sales_stock_repository import SalesStockRepository
from repositories.assessed_repository import AssessedRepository
from repositories.sales_case_repository import SalesCaseRepository
from repositories.telephone_order_repository import TelephoneOrderRepository
from services.sales_stock_service import SalesStockService
from domain.business import Order
from domain.errors import DomainError

sales=Blueprint("sales",__name__)

@sales.get("/customers")
def customers():
    query=request.args.get("q","",type=str).strip()
    rows=SalesCaseRepository(get_connection()).customers(query)
    return render_template("customers.html", customers=rows, query=query)


@sales.get("/orders/status")
def order_status():
    raw=request.args.get("customer_id","").strip()
    if raw:
        try:
            customer_id=int(raw)
        except ValueError as exc:
            raise DomainError("Voer een geldig klantnummer in.") from exc
        if customer_id<1:
            raise DomainError("Klantnummer moet positief zijn.")
    else:
        customer_id=None
    rows=SalesCaseRepository(get_connection()).order_statuses(customer_id)
    return render_template("order_status.html", orders=rows, customer_id=raw)

@sales.get("/orders")
def orders():
    query=request.args.get("q","",type=str).strip()
    quantity=request.args.get("quantity","1",type=str)
    products=SalesStockService(SalesStockRepository(get_connection())).check(query,quantity) if query else []
    return render_template("orders.html",query=query,quantity=quantity,products=products)

@sales.post("/orders/calculate-discount")
def calculate_order_discount():
    try:
        customer_id=int(request.form["customer_id"])
        subtotal=request.form["subtotal"]
    except (TypeError,ValueError,KeyError) as exc:
        raise DomainError("Klantnummer en ordertotaal zijn verplicht.") from exc
    if customer_id<=0:
        raise DomainError("Klantnummer moet positief zijn.")
    repository=AssessedRepository(get_connection())
    customer,revenue=repository.customer_revenue(customer_id,date.today().year-1)
    first_order=repository.customer_order_count(customer_id)==0
    try:
        result=Order(subtotal,revenue,first_order).calculateTotalAmount()
    except (ValueError, InvalidOperation) as exc:
        raise DomainError("Vul een geldig, niet-negatief orderbedrag in.") from exc
    return render_template("discount.html",customer=customer,annual_revenue=revenue,
                           first_order=first_order,discount=result)


def _approval_serializer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="timaflu-telefonisch-orderakkoord")


@sales.get("/orders/new")
def new_telephone_order():
    customers, products = TelephoneOrderRepository(get_connection()).form_options()
    return render_template("telephone_order.html", customers=customers, products=products,
                           today=date.today().isoformat())


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
