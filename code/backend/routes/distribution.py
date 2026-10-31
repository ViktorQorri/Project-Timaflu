from datetime import date, time
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_connection
from repositories.assessed_repository import AssessedRepository
from domain.errors import DomainError

distribution=Blueprint("distribution",__name__)

@distribution.post("/deliveries/first-attempt/delivered")
def first_attempt_delivered():
    """A first visit can succeed; only absence requires scheduling a second."""
    try:
        day = date.fromisoformat(request.form["day"])
        delivery_id = int(request.form["delivery_id"])
    except (KeyError, ValueError) as exc:
        raise DomainError("Ongeldige leveringsdatum of leveringnummer.") from exc
    if delivery_id < 1:
        raise DomainError("Leveringnummer moet positief zijn.")
    AssessedRepository(get_connection()).record_first_attempt_delivery(
        delivery_id, day, request.form.get("signature_confirmed"))
    flash("Aflevering bij het eerste bezoek geregistreerd.", "success")
    return redirect(url_for("distribution.deliveries", day=day.isoformat()))


@distribution.get("/deliveries")
def deliveries():
    try:
        day=date.fromisoformat(request.args.get("day",date.today().isoformat()))
    except (ValueError, TypeError) as exc:
        raise DomainError("Ongeldige rooster- of leveringsdatum.") from exc
    schedule=AssessedRepository(get_connection()).delivery_schedule(day)
    return render_template("deliveries.html",day=day,schedule=schedule)

@distribution.post("/deliveries/second-attempt")
def second_attempt():
    """First absence: schedule same-day second visit without a final outcome."""
    try:
        day=date.fromisoformat(request.form["day"])
        delivery_id=int(request.form["delivery_id"])
        planned=time.fromisoformat(request.form["time"])
    except (KeyError, ValueError, TypeError) as exc:
        raise DomainError("Datum, leveringnummer en tijd van de tweede poging zijn verplicht.") from exc
    if delivery_id < 1:
        raise DomainError("Leveringnummer moet positief zijn.")
    AssessedRepository(get_connection()).schedule_second_attempt(delivery_id,planned,day)
    flash("Eerste afwezigheid vastgelegd; tweede poging op dezelfde dag ingepland.", "success")
    return redirect(url_for("distribution.deliveries",day=day.isoformat()))


@distribution.post("/deliveries/second-attempt/result")
def second_attempt_result():
    """Record delivery or second absence only after the courier returns."""
    try:
        day=date.fromisoformat(request.form["day"])
        delivery_id=int(request.form["delivery_id"])
    except (KeyError, ValueError, TypeError) as exc:
        raise DomainError("Datum en leveringnummer zijn verplicht.") from exc
    if delivery_id < 1:
        raise DomainError("Leveringnummer moet positief zijn.")
    outcome=request.form.get("outcome","")
    confirmed=request.form.get("signature_confirmed")
    AssessedRepository(get_connection()).record_second_attempt_outcome(
        delivery_id,day,outcome,confirmed
    )
    flash("Uitkomst van de tweede bezorgpoging geregistreerd.", "success")
    return redirect(url_for("distribution.deliveries",day=day.isoformat()))

@distribution.post("/deliveries/failed-followup")
def failed_followup():
    """Record the new date and any costs after sales has spoken to the customer."""
    try:
        delivery_id = int(request.form["delivery_id"])
        requested_date = date.fromisoformat(request.form["requested_date"])
    except (KeyError, ValueError, TypeError) as exc:
        raise DomainError("Geldige leveringsgegevens zijn verplicht.") from exc
    if delivery_id < 1 or request.form.get("customer_contact_confirmed") != "yes":
        raise DomainError("Bevestig eerst het contact met de klant.")
    AssessedRepository(get_connection()).record_failed_delivery_followup(
        delivery_id, requested_date, request.form.get("time_slot"),
        request.form.get("extra_cost"), request.form.get("explanation", ""))
    flash("Nieuwe leverafspraak en eventuele bezorgkosten vastgelegd.", "success")
    return redirect(url_for("distribution.deliveries", day=request.form.get("day")))
