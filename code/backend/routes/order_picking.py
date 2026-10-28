from flask import Blueprint, render_template

order_picking = Blueprint("order_picking", __name__)


@order_picking.get("/order-picking")
def index():
    """Show the order picking page."""
    return render_template("order_picking.html")
