from flask import Blueprint, render_template

sales = Blueprint("sales", __name__)


@sales.get("/customers")
def customers():
    """Show the customers page."""
    return render_template("customers.html")


@sales.get("/orders")
def orders():
    """Show the orders page."""
    return render_template("orders.html")
