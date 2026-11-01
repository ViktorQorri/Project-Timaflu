"""Casus: telefonische verkoop, prijsafspraak en atomair vastgelegde reserveringen.

Een medewerker voert de order in, bespreekt tekortregels met de klant en
legt de bestelling pas vast na expliciet akkoord met een opnieuw gecontroleerd
bedrag. Er wordt geen online bestelling door een klant aangenomen.
"""
from datetime import date, datetime
from decimal import Decimal
from domain.business import Order, euro
from domain.errors import ConflictError, DomainError
from repositories.assessed_repository import AssessedRepository
from repositories.robot_order_repository import RobotOrderRepository


class TelephoneOrderRepository:
    MAX_LINES = 12

    def __init__(self, connection):
        self.db = connection

    def form_options(self):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""SELECT klant_id, bedrijfsnaam FROM Klant ORDER BY bedrijfsnaam, klant_id""")
            customers = c.fetchall()
            c.execute("""SELECT product_id, productnaam, artikelnummer, minimale_bestelhoeveelheid,
                                prijs_per_grootverpakking
                         FROM Product WHERE in_assortiment=TRUE ORDER BY productnaam""")
            products = c.fetchall()
        return customers, products

    @classmethod
    def validate(cls, customer_id, wanted, day, slot, urgent):
        try:
            customer_id = int(customer_id)
        except (TypeError, ValueError) as exc:
            raise DomainError("Kies een geldig klantnummer.") from exc
        if customer_id < 1 or slot not in ("ochtend", "middag") or urgent not in (True, False):
            raise DomainError("Kies een klant, leverdag en dagdeel.")
        if not isinstance(day, date) or day < date.today():
            raise DomainError("Een leverdatum mag niet in het verleden liggen.")
        if not isinstance(wanted, list) or not 1 <= len(wanted) <= cls.MAX_LINES:
            raise DomainError("Voer één tot twaalf verschillende medicijnen in.")
        clean = []
        used = set()
        for row in wanted:
            try:
                product_id, quantity = int(row["product_id"]), int(row["quantity"])
            except (KeyError, TypeError, ValueError) as exc:
                raise DomainError("Per bestelregel zijn product en positief aantal verplicht.") from exc
            choice = row.get("shortage", "skip")
            if (product_id < 1 or quantity < 1 or product_id in used
                    or choice not in ("skip", "later")):
                raise DomainError("Ongeldige, dubbele of onvolledige bestelregel.")
            used.add(product_id)
            clean.append({"product_id": product_id, "quantity": quantity, "shortage": choice})
        return customer_id, clean

    def quote(self, customer_id, wanted, day, slot, urgent, for_update=False):
        customer_id, wanted = self.validate(customer_id, wanted, day, slot, urgent)
        with self.db.cursor(dictionary=True) as c:
            c.execute(
                "SELECT klant_id FROM Klant WHERE klant_id=%s" +
                (" FOR UPDATE" if for_update else ""), (customer_id,)
            )
            if c.fetchone() is None:
                raise DomainError("Klant bestaat niet.")
        assessed = AssessedRepository(self.db)
        customer, revenue = assessed.customer_revenue(customer_id, date.today().year - 1)
        first_order = assessed.customer_order_count(customer_id) == 0
        lines = []
        with self.db.cursor(dictionary=True) as c:
            for requested in sorted(wanted, key=lambda item: item["product_id"]):
                pid = requested["product_id"]
                c.execute("""SELECT product_id, productnaam, artikelnummer,
                                    prijs_per_grootverpakking, minimale_bestelhoeveelheid
                             FROM Product WHERE product_id=%s AND in_assortiment=TRUE""" +
                          (" FOR UPDATE" if for_update else ""), (pid,))
                product = c.fetchone()
                if not product:
                    raise ConflictError("Het geselecteerde medicijn is niet meer leverbaar.")
                if requested["quantity"] < int(product["minimale_bestelhoeveelheid"]):
                    raise DomainError("Aantal is lager dan de minimale bestelhoeveelheid.")
                c.execute("SELECT COALESCE(SUM(aantal),0) AS physical FROM Magazijnlocatie WHERE product_id=%s", (pid,))
                physical = int(c.fetchone()["physical"])
                c.execute("SELECT COALESCE(SUM(aantal),0) AS reserved FROM Voorraadreservering WHERE product_id=%s", (pid,))
                available = max(physical - int(c.fetchone()["reserved"]), 0)
                enough = available >= requested["quantity"]
                skip = not enough and requested["shortage"] == "skip"
                lines.append({
                    **requested, **product, "available": available, "enough": enough,
                    "skipped": skip, "backorder": not enough and not skip,
                    "unit_price": euro(product["prijs_per_grootverpakking"]),
                    "line_total": euro(requested["quantity"] * Decimal(str(product["prijs_per_grootverpakking"])))
                })
        selected = [line for line in lines if not line["skipped"]]
        if not selected:
            raise DomainError("De klant neemt geen producten af. Er is geen bestelling om vast te leggen.")
        subtotal_ex_vat = euro(sum((line["line_total"] for line in selected), Decimal(0)))
        gross = euro(subtotal_ex_vat * Decimal("1.09"))
        discount = Order(gross, revenue, first_order).calculateTotalAmount()
        fingerprint = [
            [line["product_id"], line["quantity"], line["shortage"],
             str(line["unit_price"]), line["available"], line["skipped"]]
            for line in lines
        ]
        fingerprint.append([str(revenue), first_order, str(discount["total"])])
        return {
            "customer": customer, "customer_id": customer_id, "lines": lines,
            "selected": selected, "day": day, "slot": slot, "urgent": urgent,
            "subtotal_ex_vat": subtotal_ex_vat, "gross": gross,
            "discount": discount, "fingerprint": fingerprint
        }

    def approve(self, customer_id, wanted, day, slot, urgent, expected):
        """One database transaction: recheck the approved quote, reserve and assign robots."""
        try:
            quote = self.quote(customer_id, wanted, day, slot, urgent, for_update=True)
            if quote["fingerprint"] != expected:
                raise ConflictError("Voorraad, prijs of korting is gewijzigd; bespreek de nieuwe prijs opnieuw met de klant.")
            with self.db.cursor(dictionary=True) as c:
                c.execute(
                    """INSERT INTO Bestelling
                       (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                        gewenste_leverdatum, dagdeel, spoed, status_naam)
                       SELECT klant_id, afleveradres_id, betaaladres_id, %s, %s, %s, %s, %s
                       FROM Klant WHERE klant_id=%s""",
                    (datetime.now(), day, slot, urgent,
                     "backorder" if any(l["backorder"] for l in quote["selected"]) else "wordt verzameld",
                     quote["customer_id"])
                )
                order_id = c.lastrowid
                for line in quote["selected"]:
                    c.execute("""INSERT INTO Bestelregel
                                 (bestelling_id,product_id,aantal,prijs_per_eenheid,afnemen_bij_tekort)
                                 VALUES(%s,%s,%s,%s,%s)""",
                              (order_id, line["product_id"], line["quantity"],
                               line["unit_price"], line["backorder"]))
                    if line["enough"]:
                        c.execute("""INSERT INTO Voorraadreservering(bestelling_id,product_id,aantal)
                                     VALUES(%s,%s,%s)""",
                                  (order_id, line["product_id"], line["quantity"]))
            assignments = []
            if any(line["enough"] for line in quote["selected"]):
                assignments = RobotOrderRepository(self.db).generate(order_id, commit=False)
            self.db.commit()
            return {"order_id": order_id, "suborders": assignments,
                    "status": "backorder" if any(line["backorder"] for line in quote["selected"]) else "wordt verzameld"}
        except Exception:
            self.db.rollback()
            raise
