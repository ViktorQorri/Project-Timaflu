"""Sales reports for management: revenue per customer, per period and best-selling medicines."""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from domain.errors import DomainError

# MySQL DATE_FORMAT pattern per grouping. %x-W%v is the ISO year and week, like 2026-W09.
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
    """Format an amount the Dutch way, for example Decimal('1234.5') -> '€ 1.234,50'."""
    amount = Decimal(amount or 0).quantize(CENT, rounding=ROUND_HALF_UP)
    text = f"{amount:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"€ {text}"


def period_key(day, grouping):
    """Return the key MySQL's DATE_FORMAT gives this day for the grouping."""
    if grouping == "day":
        return day.isoformat()
    if grouping == "week":
        year, week, _ = day.isocalendar()
        return f"{year}-W{week:02d}"
    if grouping == "month":
        return f"{day.year}-{day.month:02d}"
    return str(day.year)


def period_label(key, grouping):
    """Return a readable Dutch label for a period key."""
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
    """Validate the report filters and combine the sales figures for the report page."""

    def __init__(self, repository):
        self.repository = repository

    def report(self, start="", end="", grouping="month", today=None):
        """Return the sales report for the period from start up to and including end.

        Args:
            start: First day as 'YYYY-MM-DD'. Empty means 1 January of the current year.
            end: Last day as 'YYYY-MM-DD'. Empty means today.
            grouping: 'day', 'week', 'month' or 'year' for revenue per period.
            today: The current date, only passed in by tests.

        Raises:
            DomainError: A date is invalid, start is after end or the grouping is unknown.
        """
        today = today or date.today()
        start = self._parse_date(start, date(today.year, 1, 1), "begindatum")
        end = self._parse_date(end, today, "einddatum")
        if start > end:
            raise DomainError("De begindatum moet op of vóór de einddatum liggen.")
        grouping = grouping or "month"
        if grouping not in PERIOD_FORMATS:
            raise DomainError("Kies een geldige indeling: dag, week, maand of jaar.")

        # The queries use a half-open period, so the whole last day is included.
        end_exclusive = end + timedelta(days=1)
        customers = self.repository.revenue_per_customer(start, end_exclusive)
        periods = self.repository.revenue_per_period(PERIOD_FORMATS[grouping], start, end_exclusive)
        products = self.repository.best_selling_products(start, end_exclusive, TOP_PRODUCTS)

        total_revenue = sum((self._money(row["omzet"]) for row in customers), Decimal("0"))
        total_orders = sum(int(row["aantal_bestellingen"]) for row in customers)
        average = (total_revenue / total_orders).quantize(CENT, rounding=ROUND_HALF_UP) if total_orders else Decimal("0.00")

        return {
            "start": start,
            "end": end,
            "grouping": grouping,
            "total_revenue": total_revenue,
            "total_orders": total_orders,
            "customer_count": len(customers),
            "average_order_value": average,
            "customers": [
                {
                    **row,
                    "omzet": self._money(row["omzet"]),
                    "aandeel": self._percentage(row["omzet"], total_revenue),
                }
                for row in customers
            ],
            "periods": self._all_periods(periods, start, end, grouping),
            "products": [
                {
                    **row,
                    "aantal_verkocht": int(row["aantal_verkocht"]),
                    "omzet": self._money(row["omzet"]),
                }
                for row in products
            ],
        }

    def _all_periods(self, rows, start, end, grouping):
        """Return every period between start and end, with zero revenue where nothing was sold."""
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
            row = found.get(key, {})
            periods.append({
                "periode": key,
                "label": period_label(key, grouping),
                "aantal_bestellingen": int(row.get("aantal_bestellingen", 0)),
                "omzet": self._money(row.get("omzet")),
            })
        highest = max((period["omzet"] for period in periods), default=Decimal("0"))
        for period in periods:
            period["breedte"] = self._percentage(period["omzet"], highest)
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
        return Decimal(value or 0).quantize(CENT, rounding=ROUND_HALF_UP)

    @staticmethod
    def _percentage(part, whole):
        if not whole:
            return Decimal("0.0")
        return (Decimal(part or 0) * 100 / whole).quantize(TENTH, rounding=ROUND_HALF_UP)
