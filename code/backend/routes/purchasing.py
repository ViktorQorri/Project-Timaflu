from flask import Blueprint, render_template

purchasing = Blueprint("purchasing", __name__)


@purchasing.get("/stock")
def stock():
    """Show the stock page."""
    return render_template("stock.html")


@purchasing.get("/suppliers")
def suppliers():
    """Show the suppliers page."""
    return render_template("suppliers.html")
