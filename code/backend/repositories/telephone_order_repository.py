"""Casus: telefonische verkoop, prijsafspraak en atomair vastgelegde reserveringen.

Een medewerker voert de order in, bespreekt tekortregels met de klant en
legt de bestelling pas vast na expliciet akkoord met een opnieuw gecontroleerd
bedrag. Er wordt geen online bestelling door een klant aangenomen.
"""
from datetime import date, datetime
from decimal import Decimal
from domain.business import euro
from domain.errors import ConflictError, DomainError
from repositories.discount_repository import DiscountRepository
from services.discount_service import DiscountService
from repositories.robot_order_repository import RobotOrderRepository


class TelephoneOrderRepository:
    def __init__(self, connection):
        self.db = connection

    def form_options(self):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""SELECT klant_id, bedrijfsnaam FROM Klant WHERE actief=TRUE ORDER BY bedrijfsnaam, klant_id""")
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
        if urgent and day != date.today():
            raise DomainError(
                "Een spoedbestelling wordt vandaag binnen maximaal drie uur geleverd."
            )
        if not urgent and day == date.today():
            raise DomainError(
                "Vandaag leveren kan alleen bij een spoedbestelling."
            )
        if not isinstance(wanted, list) or not wanted:
            raise DomainError("Voer minimaal één bestelregel in.")
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
                """SELECT k.klant_id, k.bedrijfsnaam,
                          delivery.adres AS afleveradres, billing.adres AS factuuradres
                   FROM Klant AS k
                   JOIN Adres AS delivery ON delivery.adres_id=k.afleveradres_id
                   JOIN Adres AS billing ON billing.adres_id=k.betaaladres_id
                   WHERE k.klant_id=%s AND k.actief=TRUE""" +
                (" FOR UPDATE" if for_update else ""), (customer_id,)
            )
            customer = c.fetchone()
            if customer is None:
                raise DomainError("Klant bestaat niet.")
            c.execute(
                """SELECT 1 FROM Factuur WHERE klant_id=%s AND betaald_op IS NULL
                   AND incasso_ingeschakeld=TRUE LIMIT 1""", (customer_id,)
            )
            if c.fetchone() is not None:
                raise ConflictError("Een klant bij het incassobureau kan geen nieuwe bestelling plaatsen.")
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
        # Reuse the case pricing flow and the rate fixed for this calendar year.
        # A first order receives the same single 10% incentive irrespective of acquisition.
        calculation = DiscountService(
            DiscountRepository(self.db)
        ).calculate_total_amount(
            customer_id, [(line["product_id"], line["quantity"]) for line in selected]
        )
        subtotal_ex_vat = calculation["subtotal"]
        gross = calculation["gross_total"]
        amounts = {item["kind"]: item["amount"] for item in calculation["discounts"]}
        discount = {
            "order_discount": amounts.get("order", Decimal("0.00")),
            "first_order_discount": amounts.get("one_time", Decimal("0.00")),
            "customer_discount": amounts["customer"],
            "total": calculation["total_amount"],
        }
        fingerprint = [
            [line["product_id"], line["quantity"], line["shortage"],
             str(line["unit_price"]), line["available"], line["skipped"]]
            for line in lines
        ]
        fingerprint.append([
            calculation["discount_year"],
            str(calculation["customer_discount_percentage"]),
            calculation["first_order"],
            str(discount["total"]),
            customer["bedrijfsnaam"],
            customer["afleveradres"],
            customer["factuuradres"],
        ])
        return {
            "customer": customer, "customer_id": customer_id, "lines": lines,
            "selected": selected, "day": day, "slot": slot, "urgent": urgent,
            "subtotal_ex_vat": subtotal_ex_vat, "gross": gross,
            "calculation": calculation,
            "discount": discount, "fingerprint": fingerprint
        }

    def approve(self, customer_id, wanted, day, slot, urgent, expected):
        """One database transaction: recheck the approved quote, reserve and assign robots."""
        try:
            quote = self.quote(customer_id, wanted, day, slot, urgent, for_update=True)
            if quote["fingerprint"] != expected:
                raise ConflictError("Voorraad, prijs of korting is gewijzigd; bespreek de nieuwe prijs opnieuw met de klant.")
            with self.db.cursor(dictionary=True) as c:
                calc = quote["calculation"]
                customer_id = quote["customer_id"]
                year = calc["discount_year"]
                c.execute(
                    """SELECT percentage FROM Klantkorting
                       WHERE klant_id=%s AND kalenderjaar=%s FOR UPDATE""",
                    (customer_id, year),
                )
                stored = c.fetchone()
                if stored is None:
                    # The first order of a customer registered after year-end gets
                    # the 5% baseline, recorded only after confirmed approval.
                    if not calc["first_order"]:
                        raise ConflictError("De klantenkorting voor dit jaar ontbreekt.")
                    c.execute(
                        """INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)
                           VALUES (%s,%s,%s)""",
                        (customer_id, year, calc["customer_discount_percentage"]),
                    )
                elif Decimal(stored["percentage"]) != calc["customer_discount_percentage"]:
                    raise ConflictError("De klantenkorting is gewijzigd. Vraag opnieuw akkoord.")
                c.execute(
                    """INSERT INTO Bestelling
                       (klant_id, afleveradres_id, betaaladres_id, besteld_op,
                        gewenste_leverdatum, dagdeel, spoed, status_naam,
                        eenmalige_korting_toegepast)
                       SELECT klant_id, afleveradres_id, betaaladres_id,
                              %s, %s, %s, %s, %s, %s
                       FROM Klant WHERE klant_id=%s""",
                    (datetime.now(), day, slot, urgent,
                     "backorder" if any(l["backorder"] for l in quote["selected"]) else "wordt verzameld",
                     calc["first_order"], customer_id)
                )
                order_id = c.lastrowid
                for line in quote["selected"]:
                    # NULL: no shortage decision was needed (in stock).
                    # TRUE: customer explicitly accepted delayed shortage product.
                    # FALSE is reserved for explicit shortage refusal, never for
                    # an in-stock order line that still needs delivery.
                    c.execute("""INSERT INTO Bestelregel
                                 (bestelling_id,product_id,aantal,prijs_per_eenheid,afnemen_bij_tekort)
                                 VALUES(%s,%s,%s,%s,%s)""",
                              (order_id, line["product_id"], line["quantity"],
                               line["unit_price"], True if line["backorder"] else None))
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
