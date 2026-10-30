from datetime import date
from flask import Blueprint, render_template, request
from db import get_connection
from domain.business import Invoice
from repositories.assessed_repository import AssessedRepository

administration=Blueprint("administration",__name__)

@administration.get("/invoices")
def invoices():
    customer_id=request.args.get("customer_id",type=int)
    rows=[]
    if customer_id:
        repo=AssessedRepository(get_connection())
        for row in repo.invoice_for_customer(customer_id):
            invoice=Invoice(customer_id,str(row["factuur_id"]),row["factuurdatum"],row["betaald_op"])
            doc=invoice.createWeeklyInvoice(row["bedrijfsnaam"],row["adres"],row["lines"])
            doc["action"]=invoice.checkPaymentArrears(date.today())
            rows.append(doc)
    return render_template("invoices.html",invoices=rows,customer_id=customer_id)

@administration.post("/invoices/actions")
def invoice_action():
    from flask import redirect, url_for, flash
    from domain.errors import DomainError
    invoice_id=request.form.get("invoice_id",type=int)
    customer_id=request.form.get("customer_id",type=int)
    action=request.form.get("action","")
    if not invoice_id or not customer_id:
        raise DomainError("Invoice and customer are required")
    if action not in ("reminder1","reminder2","payment_plan_accepted","payment_plan_rejected","mark_paid"):
        raise DomainError("Unknown invoice action")
    repo=AssessedRepository(get_connection())
    if action=="mark_paid":
        from domain.business import euro
        try:
            received=euro(request.form["received_amount"])
        except (ValueError,KeyError) as exc:
            raise DomainError("Valid payment amount required") from exc
        invoices_for_customer=repo.invoice_for_customer(customer_id)
        matched=next((row for row in invoices_for_customer if row["factuur_id"]==invoice_id),None)
        if matched is None:
            raise DomainError("Invoice does not belong to selected customer")
        calculated=Invoice(customer_id,str(invoice_id),matched["factuurdatum"],matched["betaald_op"]).createWeeklyInvoice(
            matched["bedrijfsnaam"],matched["adres"],matched["lines"])
        if received != calculated["total"]:
            raise DomainError("Partial payments are not permitted")
    repo.record_payment_action(invoice_id,action,date.today())
    flash("Factuur bijgewerkt.","success")
    return redirect(url_for("administration.invoices",customer_id=customer_id))
