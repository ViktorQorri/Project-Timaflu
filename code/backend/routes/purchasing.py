from flask import Blueprint, render_template, request, redirect, url_for, flash

from db import get_connection
from repositories.stock_repository import StockRepository
from services.stock_service import StockService
from repositories.supplier_repository import SupplierRepository
from services.supplier_service import SupplierService
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService
from services.reorder_service import ReorderService
from domain.errors import DomainError

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

def _reorder_service():
    connection = get_connection()
    return ReorderService(
        StockService(StockRepository(connection)),
        SupplierService(SupplierRepository(connection)),
        PurchaseOrderService(PurchaseOrderRepository(connection)),
    )


@purchasing.route("/reorder", methods=["GET", "POST"])
def reorder():
    """Prepare shortages and only persist purchases explicitly confirmed manually."""
    service = _reorder_service()
    if request.method == "POST":
        order_id = service.record_confirmed(
            request.form.get("product_id"),
            request.form.get("supplier_id"),
            request.form.get("quantity"),
            request.form.get("confirmed"),
        )
        flash(f"Inkooporder {order_id} is geregistreerd.", "success")
        return redirect(url_for("purchasing.reorder"))
    result = service.overview(request.args.get("product_id"))
    return render_template("reorder.html", **result)
