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
    # Invalid form data is a user error, even when the database is unavailable.
    prospect = AcquisitionService.validate_prospect(request.form)
    prospect_id = AcquisitionRepository(get_connection()).register_prospect(prospect)
    flash(f"Potentiële klant {prospect_id} en het bezoek zijn vastgelegd.", "success")
    return redirect(url_for("acquisition.index"))


@acquisition.post("/acquisition/prospects/<int:prospect_id>/follow-up")
def complete_follow_up(prospect_id):
    """Record the follow-up decision, converting the prospect when requested."""
    if (request.form.get("outcome") in ("no_interest", "no_consent")
            and request.form.get("decision_confirmed") != "yes"):
        from domain.errors import DomainError
        raise DomainError("Bevestig eerst de afwijzing of ontbrekende toestemming.")
    customer_id = _service().complete_follow_up(prospect_id, request.form)
    if customer_id is None:
        flash("De acquisitieopvolging is afgesloten.", "success")
    else:
        flash(
            f"Potentiële klant is klant {customer_id}; de eenmalige korting van 10% is toegekend.",
            "success",
        )
    return redirect(url_for("acquisition.index"))
