"""Management sales reports using persisted invoice totals."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from domain.errors import DomainError

PERIOD_FORMATS = {
    "day": "%Y-%m-%d",
    "week": "%x-W%v",
    "month": "%Y-%m",
    "year": "%Y",
}
TOP_PRODUCTS = 10
MONTH_NAMES = [
    "januari", "februari", "maart", "april", "mei", "juni",
    "juli", "augustus", "september", "oktober", "november", "december",
]
CENT = Decimal("0.01")
TENTH = Decimal("0.1")


def format_euro(amount):
    """Format saved invoice amounts in Dutch notation without hiding unknowns."""
    if amount is None:
        return "Onbekend"
    amount = Decimal(amount).quantize(CENT, rounding=ROUND_HALF_UP)
    text = f"{amount:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"€ {text}"


def period_key(day, grouping):
    if grouping == "day":
        return day.isoformat()
    if grouping == "week":
        year, week, _ = day.isocalendar()
        return f"{year}-W{week:02d}"
    if grouping == "month":
        return f"{day.year}-{day.month:02d}"
    return str(day.year)


def period_label(key, grouping):
    if grouping == "day":
        return date.fromisoformat(key).strftime("%d-%m-%Y")
    if grouping == "week":
        year, week = key.split("-W")
        return f"Week {int(week)}, {year}"
    if grouping == "month":
        year, month = key.split("-")
        return f"{MONTH_NAMES[int(month) - 1]} {year}"
    return key


class SalesReportService:
    def __init__(self, repository):
        self.repository = repository

    def report(self, start="", end="", grouping="month", today=None):
        """Build invoice-based revenue and delivered-quantity reports."""
        today = today or date.today()
        start = self._parse_date(start, date(today.year, 1, 1), "begindatum")
        end = self._parse_date(end, today, "einddatum")
        if start > end:
            raise DomainError("De begindatum moet op of vóór de einddatum liggen.")
        grouping = grouping or "month"
        if grouping not in PERIOD_FORMATS:
            raise DomainError("Kies een geldige indeling: dag, week, maand of jaar.")

        end_exclusive = end + timedelta(days=1)
        customers = self.repository.revenue_per_customer(start, end_exclusive)
        period_rows = self.repository.revenue_per_period(
            PERIOD_FORMATS[grouping], start, end_exclusive
        )
        products = self.repository.best_selling_products(
            start, end_exclusive, TOP_PRODUCTS
        )

        invoice_count = sum(int(row["aantal_facturen"]) for row in customers)
        known_invoice_count = sum(int(row["bekende_facturen"]) for row in customers)
        unknown_count = sum(int(row["onbekende_facturen"]) for row in customers)
        known_total = sum(
            (self._money(row["bekend_factuurbedrag"]) or Decimal("0.00")
             for row in customers),
            Decimal("0.00"),
        )
        if known_invoice_count == 0 and invoice_count:
            known_total = None
        total_revenue = known_total if unknown_count == 0 else None

        customer_rows = []
        for row in customers:
            known_amount = self._money(row["bekend_factuurbedrag"])
            unknown = int(row["onbekende_facturen"])
            if int(row["bekende_facturen"]) == 0 and int(row["aantal_facturen"]):
                known_amount = None
            customer_rows.append({
                **row,
                "bekend_factuurbedrag": known_amount,
                "omzet": known_amount if unknown == 0 else None,
                "onbekende_facturen": unknown,
                "aandeel": (
                    self._percentage(known_amount, total_revenue)
                    if unknown_count == 0 and total_revenue
                    else None
                ),
            })

        return {
            "start": start,
            "end": end,
            "grouping": grouping,
            "invoice_count": invoice_count,
            "customer_count": len(customers),
            "unknown_invoice_count": unknown_count,
            "known_invoice_total": known_total,
            "total_revenue": total_revenue,
            "average_invoice_value": (
                (total_revenue / invoice_count).quantize(
                    CENT, rounding=ROUND_HALF_UP
                )
                if total_revenue is not None and invoice_count
                else (Decimal("0.00") if total_revenue is not None else None)
            ),
            "customers": customer_rows,
            "periods": self._all_periods(period_rows, start, end, grouping),
            "products": [
                {**row, "aantal_verkocht": int(row["aantal_verkocht"])}
                for row in products
            ],
        }

    def _all_periods(self, rows, start, end, grouping):
        """Fill empty periods with zero while keeping unknown snapshots explicit."""
        found = {row["periode"]: row for row in rows}
        keys = []
        day = start
        while day <= end:
            key = period_key(day, grouping)
            if not keys or keys[-1] != key:
                keys.append(key)
            day += timedelta(days=1)

        periods = []
        for key in keys:
            row = found.get(key)
            if row is None:
                invoices = 0
                unknown = 0
                known_amount = Decimal("0.00")
                revenue = Decimal("0.00")
            else:
                invoices = int(row["aantal_facturen"])
                unknown = int(row["onbekende_facturen"])
                known_amount = self._money(row["bekend_factuurbedrag"])
                if int(row["bekende_facturen"]) == 0 and invoices:
                    known_amount = None
                revenue = known_amount if unknown == 0 else None
            periods.append({
                "periode": key,
                "label": period_label(key, grouping),
                "aantal_facturen": invoices,
                "onbekende_facturen": unknown,
                "bekend_factuurbedrag": known_amount,
                "omzet": revenue,
            })

        complete_revenues = [
            period["omzet"]
            for period in periods
            if period["omzet"] is not None
        ]
        highest = max(complete_revenues, default=Decimal("0.00"))
        for period in periods:
            period["breedte"] = (
                self._percentage(period["omzet"], highest)
                if period["omzet"] is not None and highest
                else None
            )
        return periods

    @staticmethod
    def _parse_date(value, default, name):
        value = (value or "").strip()
        if not value:
            return default
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise DomainError(f"De {name} is geen geldige datum.") from error

    @staticmethod
    def _money(value):
        if value is None:
            return None
        return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)

    @staticmethod
    def _percentage(part, whole):
        if not whole:
            return Decimal("0.0")
        return (
            Decimal(part or 0) * 100 / whole
        ).quantize(TENTH, rounding=ROUND_HALF_UP)
