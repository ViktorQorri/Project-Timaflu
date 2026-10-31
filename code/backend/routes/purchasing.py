from flask import Blueprint, render_template, request, redirect, url_for, flash

from db import get_connection
from domain.errors import DomainError, NotFoundError
from repositories.product_repository import ProductRepository
from services.product_service import ProductService
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

PRODUCT_FIELDS = (
    "article_number", "order_code", "product_name", "price_per_bulk_package", "package_type",
    "number_of_retail_packages", "short_description", "long_description",
    "minimum_order_quantity", "minimum_stock", "supplier_id", "purchase_price",
)


def product_service():
    """Build the ProductService for this request."""
    connection = get_connection()
    return ProductService(ProductRepository(connection), SupplierRepository(connection))


def product_form_data():
    """Read the product form: single values as strings, active ingredients as lists."""
    data = {key: request.form.get(key, "") for key in PRODUCT_FIELDS}
    data["ingredient_name"] = request.form.getlist("ingredient_name")
    data["ingredient_quantity"] = request.form.getlist("ingredient_quantity")
    data["ingredient_rows"] = request.form.get("ingredient_rows", "2")
    return data


def added_ingredient_row(data):
    """Preserve submitted fields and add one empty ingredient pair without JS."""
    try:
        previous = int(data["ingredient_rows"])
    except (ValueError, TypeError):
        previous = 2
    previous = max(previous, len(data["ingredient_name"]), len(data["ingredient_quantity"]), 2)
    data["ingredient_rows"] = min(previous + 1, 64)
    return data


def form_data_from_product(product):
    """Fill the product form with the saved values of a product."""
    return {
        "article_number": product.article_number,
        "order_code": product.order_code,
        "product_name": product.product_name,
        "price_per_bulk_package": product.price_per_bulk_package,
        "package_type": product.package_type or "",
        "number_of_retail_packages": product.number_of_retail_packages,
        "short_description": product.short_description or "",
        "long_description": product.long_description or "",
        "minimum_order_quantity": product.minimum_order_quantity,
        "minimum_stock": product.minimum_stock,
        "ingredient_name": [i.ingredient_name for i in product.active_ingredients],
        "ingredient_quantity": [i.quantity for i in product.active_ingredients],
    }


@purchasing.get("/products")
def products():
    """Show the product catalog."""
    return render_template("products.html", products=product_service().catalog())


@purchasing.route("/products/new", methods=["GET", "POST"])
def add_product():
    """Show the form for a new medicine, or add it to the assortment (AD24)."""
    service = product_service()
    if request.method == "POST":
        data = product_form_data()
        if request.form.get("form_action") == "add_ingredient":
            return render_template(
                "product_form.html", form=added_ingredient_row(data),
                suppliers=service.suppliers(), error=None,
            )
        try:
            service.add_product(data)
        except DomainError as error:
            return render_template(
                "product_form.html", form=data, suppliers=service.suppliers(), error=str(error)
            ), error.status_code
        flash(f"{data['product_name'].strip()} is toegevoegd aan het assortiment.", "success")
        return redirect(url_for("purchasing.products"))
    return render_template("product_form.html", form={}, suppliers=service.suppliers())


@purchasing.route("/products/<int:product_id>/edit", methods=["GET", "POST"])
def edit_product(product_id):
    """Show the form with the product data, or save the changes."""
    service = product_service()
    product = service.get_product(product_id)
    if request.method == "POST":
        data = product_form_data()
        if request.form.get("form_action") == "add_ingredient":
            return render_template(
                "product_form.html", form=added_ingredient_row(data),
                product=product, error=None,
            )
        try:
            service.update_product(product_id, data)
        except NotFoundError:
            raise
        except DomainError as error:
            return render_template(
                "product_form.html", form=data, product=product, error=str(error)
            ), error.status_code
        flash(f"{data['product_name'].strip()} is opgeslagen.", "success")
        return redirect(url_for("purchasing.products"))
    return render_template("product_form.html", form=form_data_from_product(product), product=product)


@purchasing.route("/products/<int:product_id>/remove", methods=["GET", "POST"])
def remove_product(product_id):
    """Ask for confirmation, then take the product out of the assortment."""
    service = product_service()
    if request.method == "POST":
        product = service.remove_from_assortment(product_id)
        flash(f"{product.product_name} is verwijderd uit het assortiment.", "success")
        return redirect(url_for("purchasing.products"))
    return render_template("product_remove.html", product=service.get_product(product_id))
