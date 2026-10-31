"""Generate and view persisted weekly invoices; no email is sent."""
from datetime import date, timedelta

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for

from db import get_connection
from domain.business import euro
from domain.errors import DomainError, NotFoundError
from repositories.weekly_invoice_repository import WeeklyInvoiceRepository

weekly_invoices = Blueprint("weekly_invoices", __name__)


def previous_completed_week():
    this_monday = date.today() - timedelta(days=date.today().weekday())
    return this_monday - timedelta(days=7)


def parse_week(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise DomainError("Geef een geldige maandag op (jjjj-mm-dd).") from exc


@weekly_invoices.route("/invoices/weekly", methods=["GET", "POST"])
def weekly_overview():
    week_start = parse_week(
        request.values.get("week_start", previous_completed_week().isoformat())
    )
    if request.method == "POST":
        ids = WeeklyInvoiceRepository(get_connection()).issue_week(
            week_start, current_app.config.get("TIMAFLU_ADDRESS", "")
        )
        if ids:
            flash(f"{len(ids)} weekfactuur/facturen opgeslagen.", "success")
        else:
            flash("Geen nieuwe geleverde regels; er is geen dubbele factuur gemaakt.", "info")
        return redirect(url_for("weekly_invoices.weekly_overview",
                                week_start=week_start.isoformat(),
                                created=",".join(str(i) for i in ids)))
    preview = []
    if week_start.weekday() == 0 and week_start + timedelta(days=6) < date.today():
        preview = WeeklyInvoiceRepository(get_connection()).eligible_customers(week_start)
    created = [int(part) for part in request.args.get("created", "").split(",")
               if part.isdigit()]
    return render_template(
        "weekly_invoices.html", week_start=week_start,
        customer_count=len(preview), created=created,
        sender_address=current_app.config.get("TIMAFLU_ADDRESS", ""),
    )


@weekly_invoices.get("/invoices/issued/<int:invoice_id>")
def issued_invoice(invoice_id):
    row = WeeklyInvoiceRepository(get_connection()).issued_invoice(invoice_id)
    if row is None:
        raise NotFoundError("Factuur niet gevonden.")
    amounts = {
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
    rows = [{**line, "line_total": euro(line["quantity"] * line["unit_price"])}
            for line in row["lines"]]
    return render_template(
        "issued_invoice.html", invoice=row, lines=rows, amounts=amounts,
        complete=all(amount is not None for amount in amounts.values()),
    )
