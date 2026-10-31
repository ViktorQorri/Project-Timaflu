from datetime import date
from decimal import InvalidOperation
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
            from domain.business import euro
            # The invoice has already been issued. Never invent historical
            # annual revenue, one-time eligibility or applied discounts.
            line_items = [
                {**line, "line_total": euro(line["quantity"] * line["unit_price"])}
                for line in row["lines"]
            ]
            snapshots = {
                "total_ex_vat": row["bedrag_excl_btw"],
                "vat_9_percent": row["btw_bedrag"],
                "total_incl_vat": row["bedrag_incl_btw"],
                "order_discount": row["bestellingskorting"],
                "total_after_order_discount": row["bedrag_na_bestellingskorting"],
                "first_order_discount": row["eenmalige_korting"],
                "total_after_first_order_discount": row["bedrag_na_eenmalige_korting"],
                "customer_discount": row["klantenkorting"],
                "total": row["totaal_bedrag"],
            }
            doc = {
                "invoice_number": row["factuur_id"],
                "date": row["factuurdatum"],
                "customer_name": row["bedrijfsnaam"],
                "customer_address": row.get("factuuradres") or row["adres"],
                "sender_address": row.get("afzenderadres"),
                "lines": line_items,
                "snapshot_complete": all(value is not None for value in snapshots.values()),
                "action": invoice.checkPaymentArrears(date.today()),
                **snapshots,
            }
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
    if action=="payment_plan_rejected" and request.form.get("offer_refused_confirmed") != "yes":
        raise DomainError("Bevestig dat de klant de aangeboden betalingsregeling heeft geweigerd.")
    repo=AssessedRepository(get_connection())
    # Validate invoice ownership for every mutation, not only mark_paid.
    # Otherwise a forged form can modify another customer's invoice.
    invoices_for_customer=repo.invoice_for_customer(customer_id)
    matched=next((row for row in invoices_for_customer if row["factuur_id"]==invoice_id),None)
    if matched is None:
        raise DomainError("Invoice does not belong to selected customer")
    if action=="mark_paid":
        from domain.business import euro
        try:
            received=euro(request.form["received_amount"])
        except (ValueError,KeyError,InvalidOperation) as exc:
            raise DomainError("Vul een geldig volledig ontvangen bedrag in.") from exc
        # Only the exact, originally persisted invoice amount can prove
        # a full payment, not a recalculation with guessed discounts.
        if matched["totaal_bedrag"] is None:
            raise DomainError(
                "Het oorspronkelijke factuurtotaal is niet vastgelegd. "
                "Een volledige betaling kan niet automatisch worden gecontroleerd."
            )
        if received != euro(matched["totaal_bedrag"]):
            raise DomainError("Gedeeltelijke betalingen zijn niet toegestaan.")
    repo.record_payment_action(invoice_id,action,date.today())
    flash("Factuur bijgewerkt.","success")
    return redirect(url_for("administration.invoices",customer_id=customer_id))
