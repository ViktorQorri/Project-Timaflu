from datetime import date, time
from flask import Blueprint, render_template, request, redirect, url_for, flash
from db import get_connection
from repositories.assessed_repository import AssessedRepository
from domain.errors import DomainError

distribution=Blueprint("distribution",__name__)

@distribution.get("/deliveries")
def deliveries():
    day=date.fromisoformat(request.args.get("day",date.today().isoformat()))
    schedule=AssessedRepository(get_connection()).delivery_schedule(day)
    return render_template("deliveries.html",day=day,schedule=schedule)

@distribution.post("/deliveries/second-attempt")
def second_attempt():
    """First absence: schedule same-day second visit without a final outcome."""
    day=date.fromisoformat(request.form["day"])
    delivery_id=int(request.form["delivery_id"])
    planned=time.fromisoformat(request.form["time"])
    AssessedRepository(get_connection()).schedule_second_attempt(delivery_id,planned,day)
    flash("Eerste afwezigheid vastgelegd; tweede poging op dezelfde dag ingepland.", "success")
    return redirect(url_for("distribution.deliveries",day=day.isoformat()))


@distribution.post("/deliveries/second-attempt/result")
def second_attempt_result():
    """Record delivery or second absence only after the courier returns."""
    day=date.fromisoformat(request.form["day"])
    delivery_id=int(request.form["delivery_id"])
    outcome=request.form.get("outcome","")
    confirmed=request.form.get("signature_confirmed")
    AssessedRepository(get_connection()).record_second_attempt_outcome(
        delivery_id,day,outcome,confirmed
    )
    flash("Uitkomst van de tweede bezorgpoging geregistreerd.", "success")
    return redirect(url_for("distribution.deliveries",day=day.isoformat()))
