"""Sales screens: stock checks, order status and the required discount calculation."""

from datetime import date

from flask import Blueprint, render_template, request

from db import get_connection
from domain.business import Order
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.order_status_notification_repository import OrderStatusNotificationRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.order_status_notification_service import OrderStatusNotificationService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)


@sales.get("/customers")
def customers():
    return render_template("customers.html")


@sales.get("/orders")
def orders():
    query = request.args.get("q", "", type=str).strip()
    quantity = request.args.get("quantity", "1", type=str)
    products = (
        SalesStockService(SalesStockRepository(get_connection())).check(query, quantity)
        if query else []
    )
    order_search = request.args.get("order", "", type=str).strip()
    found_orders = (
        OrderStatusNotificationService(
            OrderStatusNotificationRepository(get_connection())
        ).search(order_search)
        if order_search else []
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
    """Show recorded details so sales can answer a customer's telephone enquiry."""
    service = OrderStatusNotificationService(
        OrderStatusNotificationRepository(get_connection())
    )
    return render_template("order_status_notification.html", **service.status_overview(order_id))


@sales.post("/orders/calculate-discount")
def calculate_order_discount():
    try:
        customer_id = int(request.form["customer_id"])
        subtotal = request.form["subtotal"]
    except (TypeError, ValueError, KeyError) as exc:
        raise DomainError("Klantnummer en ordertotaal zijn verplicht.") from exc
    if customer_id <= 0:
        raise DomainError("Klantnummer moet positief zijn.")
    repository = AssessedRepository(get_connection())
    customer, revenue = repository.customer_revenue(customer_id, date.today().year - 1)
    first_order = repository.customer_order_count(customer_id) == 0
    result = Order(subtotal, revenue, first_order).calculateTotalAmount()
    return render_template(
        "discount.html",
        customer=customer,
        annual_revenue=revenue,
        first_order=first_order,
        discount=result,
    )
