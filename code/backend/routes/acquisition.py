from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from repositories.acquisition_repository import AcquisitionRepository
from services.acquisition_service import AcquisitionService

acquisition = Blueprint("acquisition", __name__)


def _service():
    """Create the acquisition service for the current request."""
    return AcquisitionService(AcquisitionRepository(get_connection()))


@acquisition.get("/acquisition")
def index():
    """Show the prospect registration form and due follow-ups."""
    return render_template(
        "acquisition.html",
        follow_ups=_service().due_follow_ups(),
    )


@acquisition.post("/acquisition/prospects")
def register_prospect():
    """Register a prospective customer and the acquisition visit."""
    prospect_id = _service().register_prospect(request.form)
    flash(f"Potentiële klant {prospect_id} en het bezoek zijn vastgelegd.", "success")
    return redirect(url_for("acquisition.index"))


@acquisition.post("/acquisition/prospects/<int:prospect_id>/follow-up")
def complete_follow_up(prospect_id):
    """Record the follow-up decision, converting the prospect when requested."""
    customer_id = _service().complete_follow_up(prospect_id, request.form)
    if customer_id is None:
        flash("De acquisitieopvolging is afgesloten.", "success")
    else:
        flash(
            f"Potentiële klant is klant {customer_id}; de eenmalige korting van 10% is toegekend.",
            "success",
        )
    return redirect(url_for("acquisition.index"))
