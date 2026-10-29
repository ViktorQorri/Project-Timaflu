from flask import Blueprint, render_template

from db import get_connection
from repositories.stock_repository import StockRepository
from services.stock_service import StockService

purchasing = Blueprint("purchasing", __name__)


@purchasing.get("/stock")
def stock():
    """Show the stock page."""
    service = StockService(StockRepository(get_connection()))
    return render_template("stock.html", shortages=service.shortages())


@purchasing.get("/suppliers")
def suppliers():
    """Show the suppliers page."""
    return render_template("suppliers.html")
