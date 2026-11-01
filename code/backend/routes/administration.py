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
                "total": (
                    row["totaal_bedrag"] - (row.get("extra_bezorgkosten_incl_btw") or 0)
                    if row["totaal_bedrag"] is not None else None
                ),
            }
            doc = {
                "invoice_number": row["factuur_id"],
                "date": row["factuurdatum"],
                "customer_name": row["bedrijfsnaam"],
                "customer_address": row.get("factuuradres") or row["adres"],
                "sender_address": row.get("afzenderadres"),
                "lines": line_items,
                "snapshot_complete": all(value is not None for value in snapshots.values()),
                "extra_delivery_costs": (
                    row["totaal_bedrag"] -
                    (row["bedrag_na_eenmalige_korting"] - row["klantenkorting"])
                    if all(row[key] is not None for key in (
                        "totaal_bedrag", "bedrag_na_eenmalige_korting", "klantenkorting"
                    )) else None
                ),
                "action": invoice.checkPaymentArrears(date.today()),
                "extra_cost_ex": row.get("extra_bezorgkosten_excl_btw") or 0,
                "extra_cost_vat": row.get("extra_bezorgkosten_btw") or 0,
                "extra_cost_gross": row.get("extra_bezorgkosten_incl_btw") or 0,
                "final_total": row["totaal_bedrag"],
                **snapshots,
            }
            rows.append(doc)
    repository = AssessedRepository(get_connection())
    purchase_invoices = repository.outstanding_purchase_invoices()
    uninvoiced_deliveries = repository.uninvoiced_deliveries()
    return render_template(
        "invoices.html", invoices=rows, customer_id=customer_id,
        purchase_invoices=purchase_invoices,
        uninvoiced_deliveries=uninvoiced_deliveries,
        today=date.today().isoformat()
    )


@administration.post("/invoices/annual-discounts")
def determine_annual_discounts():
    """Fix next calendar year's annual customer discounts on December 31."""
    from flask import redirect, url_for, flash
    from domain.errors import DomainError

    if request.form.get("discounts_confirmed") != "yes":
        raise DomainError("Bevestig de jaarlijkse berekening van de klantkortingen.")
    count = AssessedRepository(get_connection()).determine_annual_customer_discounts()
    flash(f"Klantkortingen voor {date.today().year + 1} vastgesteld voor {count} klanten.", "success")
    return redirect(url_for("administration.invoices"))


@administration.post("/purchase-invoices/<int:invoice_id>/paid")
def pay_purchase_invoice(invoice_id):
    """Record a supplier invoice as paid after the employee confirms payment."""
    from flask import flash, redirect, url_for
    from domain.errors import DomainError

    if request.form.get("payment_confirmed") != "yes":
        raise DomainError("Bevestig dat de inkoopfactuur daadwerkelijk is betaald.")
    AssessedRepository(get_connection()).mark_purchase_invoice_paid(
        invoice_id, date.today()
    )
    flash(f"Betaling van inkoopfactuur {invoice_id} geregistreerd.", "success")
    return redirect(url_for("administration.invoices"))


@administration.get("/invoices/outstanding")
def outstanding_invoices():
    """AD18: unpaid invoices across customers and recommended next action."""
    invoices = AssessedRepository(get_connection()).unpaid_invoice_overview(date.today())
    return render_template("outstanding_invoices.html", invoices=invoices)


@administration.get("/invoices/<int:invoice_id>/reminders/<int:sequence>")
def printable_reminder(invoice_id, sequence):
    """Produce a postal reminder; do not record it as sent when merely opened."""
    invoice = AssessedRepository(get_connection()).reminder_document(
        invoice_id, sequence, date.today()
    )
    return render_template(
        "payment_reminder.html", invoice=invoice, sequence=sequence, today=date.today()
    )


@administration.post("/invoices/<int:invoice_id>/reminders/<int:sequence>/sent")
def reminder_sent(invoice_id, sequence):
    """Record dispatch only after the employee confirms actual physical sending."""
    from flask import flash, redirect, url_for
    from domain.errors import DomainError

    if request.form.get("sent_confirmed") != "yes":
        raise DomainError("Bevestig dat je de betalingsherinnering werkelijk hebt verzonden.")
    today = date.today()
    repository = AssessedRepository(get_connection())
    repository.reminder_document(invoice_id, sequence, today)
    repository.record_payment_action(invoice_id, f"reminder{sequence}", today)
    flash(f"Herinnering {sequence} als verzonden geregistreerd.", "success")
    return redirect(url_for("administration.outstanding_invoices"))


@administration.post("/invoices/actions")
def invoice_action():
    from flask import redirect, url_for, flash
    from domain.errors import DomainError
    invoice_id=request.form.get("invoice_id",type=int)
    customer_id=request.form.get("customer_id",type=int)
    action=request.form.get("action","")
    if not invoice_id or not customer_id:
        raise DomainError("Invoice and customer are required")
    if action not in ("payment_plan_accepted", "payment_plan_rejected", "mark_paid"):
        raise DomainError(
            "Herinneringen worden na het verzenden via het herinneringsscherm geregistreerd."
        )
    if action=="payment_plan_rejected":
        if request.form.get("offer_refused_confirmed") != "yes":
            raise DomainError(
                "Bevestig dat de klant de aangeboden betalingsregeling heeft geweigerd."
            )
        if request.form.get("agency_acceptance_confirmed") != "yes":
            raise DomainError(
                "Bevestig dat het incassobureau de opdracht heeft geaccepteerd."
            )
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
