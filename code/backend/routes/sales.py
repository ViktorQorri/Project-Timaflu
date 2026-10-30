from flask import Blueprint, render_template, request

from db import get_connection
from repositories.sales_stock_repository import SalesStockRepository
from services.sales_stock_service import SalesStockService

sales = Blueprint("sales", __name__)


@sales.get("/customers")
def customers():
    """Show the customers page."""
    return render_template("customers.html")


@sales.get("/orders")
def orders():
    """Show the orders page."""
    query = request.args.get("q", "", type=str).strip()
    quantity = request.args.get("quantity", "1", type=str)
    products = SalesStockService(SalesStockRepository(get_connection())).check(query, quantity) if query else []
    return render_template("orders.html", query=query, quantity=quantity, products=products)
