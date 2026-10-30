from flask import Blueprint, render_template, request, redirect, url_for, flash

from db import get_connection
from repositories.stock_repository import StockRepository
from services.stock_service import StockService
from repositories.supplier_repository import SupplierRepository
from services.supplier_service import SupplierService
from repositories.purchase_order_repository import PurchaseOrderRepository
from services.purchase_order_service import PurchaseOrderService
from repositories.manufacturer_repository import ManufacturerRepository
from services.manufacturer_service import ManufacturerService
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

def _manufacturer_service():
    return ManufacturerService(ManufacturerRepository(get_connection()))


@purchasing.get("/manufacturers")
def manufacturers():
    return render_template(
        "manufacturers.html",
        manufacturers=_manufacturer_service().list_manufacturers(),
    )


@purchasing.route("/manufacturers/new", methods=["GET", "POST"])
def manufacturer_new():
    if request.method == "POST":
        try:
            _manufacturer_service().create(request.form)
        except DomainError as error:
            return render_template(
                "manufacturer_form.html", edit=False, values=request.form,
                error=str(error),
            ), error.status_code
        flash("Fabrikant opgeslagen.", "success")
        return redirect(url_for("purchasing.manufacturers"))
    return render_template("manufacturer_form.html", edit=False, values={}, error=None)


@purchasing.route("/manufacturers/<int:supplier_id>/edit", methods=["GET", "POST"])
def manufacturer_edit(supplier_id):
    service = _manufacturer_service()
    if request.method == "POST":
        try:
            service.update(supplier_id, request.form)
        except DomainError as error:
            return render_template(
                "manufacturer_form.html", edit=True, values=request.form,
                error=str(error),
            ), error.status_code
        flash("Fabrikant bijgewerkt.", "success")
        return redirect(url_for("purchasing.manufacturers"))
    return render_template(
        "manufacturer_form.html", edit=True,
        values=service.manufacturer(supplier_id), error=None,
    )


@purchasing.route("/manufacturers/<int:supplier_id>/prices", methods=["GET", "POST"])
def manufacturer_prices(supplier_id):
    service = _manufacturer_service()
    manufacturer = service.manufacturer(supplier_id)
    error = None
    if request.method == "POST":
        try:
            service.set_price(supplier_id, request.form.get("product_id"),
                              request.form.get("price"))
        except DomainError as failure:
            error = str(failure)
        else:
            flash("Inkoopprijs opgeslagen.", "success")
            return redirect(url_for("purchasing.manufacturer_prices",
                                    supplier_id=supplier_id))
    return render_template(
        "manufacturer_prices.html",
        manufacturer=manufacturer,
        products=service.list_products(),
        offers=service.prices(supplier_id),
        error=error,
    ), (400 if error else 200)
