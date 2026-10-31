from flask import Blueprint, flash, redirect, render_template, url_for

from db import get_connection
from domain.errors import DomainError
from repositories.picking_bin_repository import PickingBinRepository
from repositories.robot_order_repository import RobotOrderRepository
from services.picking_bin_service import PickingBinService
from services.robot_order_service import RobotOrderService


order_picking = Blueprint("order_picking", __name__)


@order_picking.get("/order-picking")
def index():
    """Show registered bins and orders ready to be assigned to robots."""
    connection = get_connection()
    bins = PickingBinService(PickingBinRepository(connection)).bins()
    orders = RobotOrderRepository(connection).orders_ready_for_dispatch()
    return render_template("order_picking.html", bins=bins, orders=orders)


@order_picking.post("/order-picking/orders/<int:order_id>/dispatch")
def dispatch_order(order_id):
    """Split an order's reserved quantities across available robot aisles."""
    service = RobotOrderService(RobotOrderRepository(get_connection()))
    try:
        assignments = service.generate_suborders(order_id)
    except DomainError as error:
        flash(str(error), "error")
    else:
        flash(
            f"Bestelling {order_id} verdeeld over {len(assignments)} robotdeelorders.",
            "success",
        )
    return redirect(url_for("order_picking.index"))
