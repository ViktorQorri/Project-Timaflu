from flask import Blueprint, render_template

reports = Blueprint("reports", __name__)


@reports.get("/reports")
def index():
    """Show the reports page."""
    return render_template("reports.html")
