from flask import Blueprint, render_template, request

from db import get_connection
from repositories.order_status_notification_repository import OrderStatusNotificationRepository
from repositories.sales_stock_repository import SalesStockRepository
from services.order_status_notification_service import OrderStatusNotificationService
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)


@sales.get("/customers")
def customers():
    """Show the customers page."""
    return render_template("customers.html")


@sales.get("/orders")
def orders():
    """Show the orders page: the stock check and the order status lookup."""
    query = request.args.get("q", "", type=str).strip()
    quantity = request.args.get("quantity", "1", type=str)
    products = SalesStockService(SalesStockRepository(get_connection())).check(query, quantity) if query else []
    order_search = request.args.get("order", "", type=str).strip()
    found_orders = (
        OrderStatusNotificationService(OrderStatusNotificationRepository(get_connection())).search(order_search)
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
    """Show the status, delivery moment and backorders of one order, with a message for the customer."""
    service = OrderStatusNotificationService(OrderStatusNotificationRepository(get_connection()))
    return render_template("order_status_notification.html", **service.status_overview(order_id))
