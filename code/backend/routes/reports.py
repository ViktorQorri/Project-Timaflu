from flask import Blueprint, render_template, request

from db import get_connection
from repositories.order_status_report_repository import OrderStatusReportRepository
from services.order_status_report_service import OrderStatusReportService

reports = Blueprint("reports", __name__)


@reports.get("/reports")
def index():
    """Show the reports page with the order status report."""
    service = OrderStatusReportService(OrderStatusReportRepository(get_connection()))
    report = service.report(
        request.args.get("from", "", type=str),
        request.args.get("to", "", type=str),
    )
    return render_template("reports.html", report=report)
