from flask import Blueprint, render_template

from db import get_connection
from repositories.order_status_report_repository import OrderStatusReportRepository
from services.order_status_report_service import OrderStatusReportService

reports = Blueprint("reports", __name__)


@reports.get("/reports")
def index():
    """Show current order statuses; no unsupported period-based reporting rules."""
    service = OrderStatusReportService(OrderStatusReportRepository(get_connection()))
    return render_template("reports.html", report=service.report())
