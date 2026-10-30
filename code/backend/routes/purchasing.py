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
    flash(f"Purchasing order {order_id} recorded after supplier confirmation.", "success")
    return redirect(url_for("purchasing.suppliers"))


@purchasing.post("/suppliers/remove-offer")
def remove_offer():
    product_id = request.form.get("product_id", type=int)
    supplier_id = request.form.get("supplier_id", type=int)
    if not product_id or not supplier_id or min(product_id, supplier_id) < 1:
        from domain.errors import DomainError
        raise DomainError("Product and supplier required.")
    SupplierRepository(get_connection()).remove_offer(product_id, supplier_id)
    flash("Leverancierskoppeling verwijderd.", "success")
    return redirect(url_for("purchasing.suppliers"))


@purchasing.post("/suppliers/remove-product")
def remove_product_from_reorder_list():
    product_id = request.form.get("product_id", type=int)
    if not product_id or product_id < 1:
        from domain.errors import DomainError
        raise DomainError("Product required.")
    SupplierRepository(get_connection()).remove_from_internal_reorder_list(product_id)
    flash("Product uit interne bestellijst verwijderd.", "success")
    return redirect(url_for("purchasing.suppliers"))
