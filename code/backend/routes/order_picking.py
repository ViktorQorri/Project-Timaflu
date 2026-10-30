from flask import Blueprint, render_template

from db import get_connection
from repositories.picking_bin_repository import PickingBinRepository
from services.picking_bin_service import PickingBinService

order_picking = Blueprint("order_picking", __name__)


@order_picking.get("/order-picking")
def index():
    """Show which order is in which picking bin. The robots register the bins through the API."""
    service = PickingBinService(PickingBinRepository(get_connection()))
    return render_template("order_picking.html", bins=service.bins())
