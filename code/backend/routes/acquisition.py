from datetime import date
from calendar import monthrange
from flask import Blueprint, render_template, request, redirect, flash, url_for
from db import get_connection
from repositories.assessed_repository import AssessedRepository
from domain.business import AcquisitionVisit, ProspectiveCustomer
from domain.errors import DomainError

acquisition=Blueprint("acquisition",__name__)

def previous_month(day):
    m=day.month-1 or 12
    y=day.year-int(day.month==1)
    return date(y,m,min(day.day,monthrange(y,m)[1]))

@acquisition.get("/acquisition")
def index():
    prospects=AssessedRepository(get_connection()).prospect_followups(previous_month(date.today()))
    return render_template("acquisition.html",prospects=prospects)

@acquisition.post("/acquisition/visits")
def record_visit():
    company=request.form.get("company","").strip()
    contact=request.form.get("contact","").strip()
    details=request.form.get("details","").strip()
    address=request.form.get("address","").strip()
    try:
        visit_date=date.fromisoformat(request.form["visit_date"])
    except (KeyError, ValueError) as exc:
        from domain.errors import DomainError
        raise DomainError("Bezoekdatum is ongeldig.") from exc
    if visit_date > date.today():
        raise DomainError("Een acquisitiebezoek kan niet in de toekomst liggen.")
    try:
        AcquisitionVisit().recordVisit(company,contact,details,address,visit_date)
    except ValueError as exc:
        raise DomainError(str(exc)) from exc
    AssessedRepository(get_connection()).record_visit(company,contact,details,address,visit_date)
    flash("Bezoek geregistreerd.","success")
    return redirect(url_for("acquisition.index"))

@acquisition.post("/acquisition/convert")
def create_customer():
    try:
        prospect_id=int(request.form["prospect_id"])
    except (KeyError, ValueError) as exc:
        raise DomainError("Ongeldig prospectnummer.") from exc
    if prospect_id < 1:
        raise DomainError("Ongeldig prospectnummer.")
    billing=request.form.get("billing_address","").strip()
    delivery=request.form.get("delivery_address","").strip()
    if request.form.get("consent")!="yes":
        from domain.errors import DomainError
        raise DomainError("Klant moet akkoord zijn met het aanmaken van het account.")
    if not billing or not delivery:
        from domain.errors import DomainError
        raise DomainError("Factuur- en afleveradres zijn verplicht.")
    customer_id=AssessedRepository(get_connection()).register_prospect_customer(prospect_id,billing,delivery)
    flash(f"Klant {customer_id} aangemaakt; 10% eenmalige korting op eerste bestelling vermelden.","success")
    return redirect(url_for("acquisition.index"))

@acquisition.post("/acquisition/decline")
def decline_followup():
    """Original case: after rejecting the incentive, stop further acquisition."""
    try:
        prospect_id=int(request.form["prospect_id"])
    except (KeyError, ValueError) as exc:
        raise DomainError("Ongeldig prospectnummer.") from exc
    if prospect_id < 1 or request.form.get("declined") != "yes":
        raise DomainError("Bevestig dat de apotheek geen interesse heeft.")
    AssessedRepository(get_connection()).close_prospect_followup(
        prospect_id, previous_month(date.today())
    )
    flash("Acquisitieopvolging afgesloten; geen verdere actie.", "success")
    return redirect(url_for("acquisition.index"))
