from flask import Blueprint, render_template

administration = Blueprint("administration", __name__)


@administration.get("/invoices")
def invoices():
    """Show the invoices page."""
    return render_template("invoices.html")
