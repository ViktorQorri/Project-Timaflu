"""Read-only overview of existing order statuses (case: Desired-process.md)."""

from flask import Blueprint, render_template

from db import get_connection
from repositories.order_status_report_repository import OrderStatusReportRepository

reports = Blueprint("reports", __name__)


@reports.get("/reports")
def index():
    """Display the recorded status and delivery information of each order."""
    orders = OrderStatusReportRepository(get_connection()).list_orders()
    return render_template("reports.html", orders=orders)
