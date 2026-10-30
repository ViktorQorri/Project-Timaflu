from flask import Blueprint, render_template, request, redirect, url_for, flash

from db import get_connection
from repositories.stock_repository import StockRepository
from services.stock_service import StockService
from repositories.supplier_repository import SupplierRepository
from services.supplier_service import SupplierService
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService

purchasing = Blueprint("purchasing", __name__)


@purchasing.get("/stock")
def stock():
    """Show the stock page."""
    service = StockService(StockRepository(get_connection()))
    return render_template("stock.html", shortages=service.shortages())


@purchasing.get("/suppliers")
def suppliers():
    """Show the suppliers page."""
    product_name = request.args.get("product", "", type=str).strip()
    service = SupplierService(SupplierRepository(get_connection())) if product_name else None
    offers = service.offers_for_product(product_name) if service else []
    return render_template("suppliers.html", product_name=product_name, offers=offers)


@purchasing.post("/purchase-orders")
def record_purchase_order():
    """Record a purchase after the employee confirms contacting a supplier."""
    service = PurchaseOrderService(PurchaseOrderRepository(get_connection()))
    order_id = service.record_order(
        request.form.get("supplier_id"),
        request.form.get("product_id"),
        request.form.get("quantity"),
    )
    flash(f"Inkooporder {order_id} is vastgelegd na bevestiging door de leverancier.", "success")
    return redirect(url_for("purchasing.suppliers"))

@purchasing.get("/stock/minimums")
def stock_minimums():
    """Manage minimum stock alerts for every catalog item."""
    service = StockService(StockRepository(get_connection()))
    return render_template("stock_minimums.html", products=service.minimums())


@purchasing.post("/stock/minimums/<int:product_id>")
def set_stock_minimum(product_id):
    """Store a manually chosen threshold and return to the overview."""
    service = StockService(StockRepository(get_connection()))
    service.set_minimum(product_id, request.form.get("minimumvoorraad"))
    flash("Minimumvoorraad bijgewerkt.", "success")
    return redirect(url_for("purchasing.stock_minimums"))
