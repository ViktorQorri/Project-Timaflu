from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from repositories.distribution_repository import DistributionRepository
from services.distribution_service import DistributionService

distribution = Blueprint("distribution", __name__)


def _service():
    """Create the distribution service for the current request."""
    return DistributionService(DistributionRepository(get_connection()))


@distribution.get("/deliveries")
def deliveries():
    """Show orders grouped by their registered collection bins."""
    return render_template(
        "deliveries.html",
        orders=_service().orders_with_bins(),
    )


@distribution.post("/deliveries/<int:order_id>/pack")
def pack_order(order_id):
    """Record the moving-box count for a completely picked order."""
    _service().pack_order(order_id, request.form.get("box_count"))
    flash(f"Bestelling {order_id} is verpakt.", "success")
    return redirect(url_for("distribution.deliveries"))


@distribution.post("/deliveries/<int:order_id>/release")
def release_order(order_id):
    """Release a packed order for distribution."""
    _service().release_order(order_id)
    flash(f"Bestelling {order_id} is vrijgegeven voor distributie.", "success")
    return redirect(url_for("distribution.deliveries"))
