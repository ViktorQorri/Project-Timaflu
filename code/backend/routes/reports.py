"""Read-only order status report and AD06 lookup for telephone sales."""

from flask import Blueprint, render_template, request

from db import get_connection
from domain.errors import NotFoundError
from repositories.order_status_report_repository import OrderStatusReportRepository

reports = Blueprint("reports", __name__)


@reports.get("/reports")
def index():
    """Show all orders or search by number/customer name (AD06)."""
    search = request.args.get("order", "", type=str).strip()
    repository = OrderStatusReportRepository(get_connection())
    orders = repository.search_orders(search) if search else repository.list_orders()
    return render_template("reports.html", orders=orders, search=search)


@reports.get("/reports/<int:order_id>")
def detail(order_id):
    """AD06: select an order and inspect its status, lines and delivery time."""
    repository = OrderStatusReportRepository(get_connection())
    order = repository.find_order(order_id)
    if order is None:
        raise NotFoundError("Geen order gevonden.")
    lines = repository.list_order_lines(order_id)
    return render_template("order_status_detail.html", order=order, lines=lines)
