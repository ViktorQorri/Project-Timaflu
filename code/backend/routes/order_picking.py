from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.errors import DomainError
from repositories.picking_bin_repository import PickingBinRepository
from services.picking_bin_service import AISLES, PickingBinService

order_picking = Blueprint("order_picking", __name__)

BIN_FIELDS = ("bin_code", "sub_order_id", "aisle")


@order_picking.get("/order-picking")
def index():
    """Show the registered picking bins and the form to register one."""
    service = PickingBinService(PickingBinRepository(get_connection()))
    return render_template("order_picking.html", bins=service.bins(), aisles=AISLES, form={})


@order_picking.post("/order-picking/bins")
def register_bin():
    """Link a scanned picking bin to a sub-order and its aisle.

    A rejected bin shows the page again with the message under the fields and the input kept.
    """
    form = {field: request.form.get(field, "") for field in BIN_FIELDS}
    service = PickingBinService(PickingBinRepository(get_connection()))
    try:
        registered = service.register(form["bin_code"], form["sub_order_id"], form["aisle"])
    except DomainError as error:
        page = render_template(
            "order_picking.html", bins=service.bins(), aisles=AISLES, form=form, error=str(error)
        )
        return page, error.status_code
    flash(
        f"Verzamelbak {registered['unieke_code']} is gekoppeld aan order {registered['bestelling_id']} "
        f"(deelorder {registered['deelorder_id']}, gang {registered['gang']}).",
        "success",
    )
    return redirect(url_for("order_picking.index"))
