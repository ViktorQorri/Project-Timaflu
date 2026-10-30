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
    day=date.fromisoformat(request.form["day"])
    delivery_id=int(request.form["delivery_id"])
    delivered=request.form.get("outcome")=="afgeleverd"
    planned=time.fromisoformat(request.form["time"])
    AssessedRepository(get_connection()).register_delivery_attempt(delivery_id,delivered,planned)
    flash("Tweede bezorgpoging geregistreerd.","success")
    return redirect(url_for("distribution.deliveries",day=day.isoformat()))
