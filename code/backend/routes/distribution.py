from datetime import date, time

from flask import Blueprint, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.distribution_repository import DistributionRepository
from services.distribution_service import DistributionService


distribution = Blueprint("distribution", __name__)


def _service():
    """Create the distribution service for the current request."""
    return DistributionService(DistributionRepository(get_connection()))


@distribution.get("/deliveries")
def deliveries():
    """Show the delivery schedule and orders grouped by their collection bins."""
    day_value = request.args.get("day") or date.today().isoformat()
    try:
        day = date.fromisoformat(day_value)
    except ValueError as error:
        raise DomainError("Vul een geldige bezorgdatum in.") from error

    connection = get_connection()
    service = DistributionService(DistributionRepository(connection))
    orders = service.orders_with_bins()
    unscheduled_orders = service.orders_to_schedule()
    couriers = service.couriers()
    schedule = AssessedRepository(connection).delivery_schedule(day)
    second_attempts = {
        row["levering_id"] for row in schedule if row["pogingnummer"] == 2
    }
    for row in schedule:
        row["can_register_first_attempt"] = (
            row["pogingnummer"] == 1 and row["resultaat"] is None
        )
        row["can_register_second_attempt"] = (
            row["pogingnummer"] == 1
            and row["resultaat"] != "afgeleverd"
            and row["levering_id"] not in second_attempts
        )
    return render_template(
        "deliveries.html",
        day=day,
        schedule=schedule,
        orders=orders,
        unscheduled_orders=unscheduled_orders,
        couriers=couriers,
    )


@distribution.post("/deliveries/couriers")
def create_courier():
    service = _service()
    service.create_courier(request.form.get("name"))
    flash(
        "Koerier toegevoegd. Registreer de koerier als beschikbaar om ritten toe te wijzen.",
        "success",
    )
    return redirect(url_for("distribution.deliveries"))


@distribution.post("/deliveries/couriers/<int:courier_id>/availability")
def update_courier_availability(courier_id):
    available_value = request.form.get("available")
    if available_value not in {"0", "1"}:
        raise DomainError("Kies een geldige beschikbaarheidsstatus.")
    _service().set_courier_availability(courier_id, available_value == "1")
    flash("Beschikbaarheid van koerier bijgewerkt.", "success")
    return redirect(url_for("distribution.deliveries"))


@distribution.post("/deliveries/schedule")
def schedule_delivery():
    try:
        order_id = int(request.form["order_id"])
        courier_id = int(request.form["courier_id"])
        planned_time = time.fromisoformat(request.form["time"])
    except (KeyError, TypeError, ValueError) as error:
        raise DomainError("Kies een bestelling, koerier en geldige bezorgtijd.") from error
    delivery_date = _service().schedule_delivery(order_id, courier_id, planned_time)
    flash("Levering ingepland.", "success")
    return redirect(
        url_for("distribution.deliveries", day=delivery_date.isoformat())
    )


@distribution.post("/deliveries/first-attempt")
def first_attempt():
    """Record the first delivery attempt and delivered order lines."""
    try:
        day = date.fromisoformat(request.form["day"])
        delivery_id = int(request.form["delivery_id"])
    except (KeyError, TypeError, ValueError) as error:
        raise DomainError("Vul een geldige bezorgdatum en levering in.") from error
    if delivery_id < 1:
        raise DomainError("Levering moet een positief geheel getal zijn.")

    outcome = request.form.get("outcome")
    if outcome not in {"afgeleverd", "niet aanwezig"}:
        raise DomainError("Kies een geldige uitkomst voor de eerste bezorgpoging.")

    AssessedRepository(get_connection()).register_first_delivery_attempt(
        delivery_id, day, outcome == "afgeleverd"
    )
    flash("Eerste bezorgpoging geregistreerd.", "success")
    return redirect(url_for("distribution.deliveries", day=day.isoformat()))


@distribution.post("/deliveries/second-attempt")
def second_attempt():
    """Record the second delivery attempt for a scheduled delivery."""
    try:
        day = date.fromisoformat(request.form["day"])
        delivery_id = int(request.form["delivery_id"])
        planned_time = time.fromisoformat(request.form["time"])
    except (KeyError, TypeError, ValueError) as error:
        raise DomainError("Vul een geldige bezorgdatum, tijd en levering in.") from error
    if delivery_id < 1:
        raise DomainError("Levering moet een positief geheel getal zijn.")

    outcome = request.form.get("outcome")
    if outcome not in {"afgeleverd", "niet aanwezig"}:
        raise DomainError("Kies een geldige uitkomst voor de tweede bezorgpoging.")

    AssessedRepository(get_connection()).register_delivery_attempt(
        delivery_id,
        day,
        outcome == "afgeleverd",
        planned_time,
    )
    flash("Tweede bezorgpoging geregistreerd.", "success")
    return redirect(url_for("distribution.deliveries", day=day.isoformat()))


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
