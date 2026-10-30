from flask import Blueprint, render_template, request

from db import get_connection
from domain.errors import DomainError
from repositories.sales_report_repository import SalesReportRepository
from services.sales_report_service import SalesReportService, format_euro

reports = Blueprint("reports", __name__)
reports.add_app_template_filter(format_euro, "euro")


@reports.get("/reports")
def index():
    """Show the reports page."""
    return render_template("reports.html")


@reports.get("/reports/sales")
def sales_report():
    """Show revenue per customer, revenue per period and the best-selling medicines."""
    filters = {
        "start": request.args.get("start", "", type=str).strip(),
        "end": request.args.get("end", "", type=str).strip(),
        "grouping": request.args.get("grouping", "month", type=str).strip(),
    }
    service = SalesReportService(SalesReportRepository(get_connection()))
    try:
        report = service.report(**filters)
    except DomainError as error:
        # Keep the filter form on screen so the user can correct the period.
        return render_template("sales_reports.html", filters=filters, report=None, error=str(error)), error.status_code
    filters = {
        "start": report["start"].isoformat(),
        "end": report["end"].isoformat(),
        "grouping": report["grouping"],
    }
    return render_template("sales_reports.html", filters=filters, report=report, error=None)
