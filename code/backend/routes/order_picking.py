from flask import Blueprint, render_template, redirect, url_for, flash

from db import get_connection
from repositories.picking_bin_repository import PickingBinRepository
from repositories.distribution_preparation_repository import DistributionPreparationRepository
from services.picking_bin_service import PickingBinService

order_picking = Blueprint("order_picking", __name__)


@order_picking.get("/order-picking")
def index():
    """Show which order is in which picking bin. The robots register the bins through the API."""
    service = PickingBinService(PickingBinRepository(get_connection()))
    ready = DistributionPreparationRepository(get_connection()).ready_to_pack()
    return render_template("order_picking.html", bins=service.bins(), ready_orders=ready)


@order_picking.post("/order-picking/orders/<int:order_id>/pack")
def pack(order_id):
    delivery_id = DistributionPreparationRepository(get_connection()).pack(order_id)
    flash(f"Verpakking geregistreerd als levering {delivery_id}. Plan nu de koerier.", "success")
    return redirect(url_for("distribution.deliveries"))
