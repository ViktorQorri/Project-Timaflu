"""MySQL queries for the five assessed scenarios, using the existing case tables."""
from datetime import date, time, timedelta
from domain.errors import ConflictError, DomainError, NotFoundError


# AD12: A successful shipment does not mean every line of the customer order
# was delivered. Only mark the full order as delivered once all order lines
# still accepted by the customer have their signed delivery quantity recorded.
# A declined shortage (afnemen_bij_tekort = FALSE) does not require delivery.
MARK_ORDER_DELIVERED_IF_COMPLETE = """
    UPDATE Bestelling AS b
    JOIN Levering AS l ON l.bestelling_id = b.bestelling_id
    SET b.status_naam = 'afgeleverd'
    WHERE l.levering_id = %s
      AND EXISTS (
          SELECT 1 FROM Bestelregel AS br
          WHERE br.bestelling_id = b.bestelling_id
            AND (
                br.afnemen_bij_tekort IS NOT FALSE
                OR EXISTS (
                    SELECT 1 FROM Voorraadreservering AS vr
                    WHERE vr.bestelling_id = br.bestelling_id AND vr.product_id = br.product_id
                )
                OR EXISTS (
                    SELECT 1 FROM Deelorder AS d
                    JOIN Deelorderregel AS dr ON dr.deelorder_id = d.deelorder_id
                    WHERE d.bestelling_id = br.bestelling_id AND dr.product_id = br.product_id
                )
                OR EXISTS (
                    SELECT 1 FROM Levering AS historic
                    JOIN Leveringregel AS hl ON hl.levering_id = historic.levering_id
                    WHERE historic.bestelling_id = br.bestelling_id AND hl.product_id = br.product_id
                )
            )
      )
      AND NOT EXISTS (
          SELECT 1 FROM Bestelregel AS br
          WHERE br.bestelling_id = b.bestelling_id
            AND (
                br.afnemen_bij_tekort IS NOT FALSE
                OR EXISTS (
                    SELECT 1 FROM Voorraadreservering AS vr
                    WHERE vr.bestelling_id = br.bestelling_id AND vr.product_id = br.product_id
                )
                OR EXISTS (
                    SELECT 1 FROM Deelorder AS d
                    JOIN Deelorderregel AS dr ON dr.deelorder_id = d.deelorder_id
                    WHERE d.bestelling_id = br.bestelling_id AND dr.product_id = br.product_id
                )
                OR EXISTS (
                    SELECT 1 FROM Levering AS historic
                    JOIN Leveringregel AS hl ON hl.levering_id = historic.levering_id
                    WHERE historic.bestelling_id = br.bestelling_id AND hl.product_id = br.product_id
                )
            )
            AND br.aantal <> COALESCE((
                SELECT SUM(lr.aantal_geleverd)
                FROM Levering AS previous
                JOIN Leveringregel AS lr ON lr.levering_id = previous.levering_id
                WHERE previous.bestelling_id = br.bestelling_id
                  AND lr.product_id = br.product_id
                  AND EXISTS (
                      SELECT 1 FROM Leverpoging AS lp
                      WHERE lp.levering_id = previous.levering_id
                        AND lp.resultaat = 'afgeleverd'
                        AND lp.ontvangst_getekend = TRUE
                  )
            ), 0)
      )
"""


class AssessedRepository:
    def __init__(self, connection):
        self.db = connection

    def customer_revenue(self, customer_id, year):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""SELECT k.klant_id, k.bedrijfsnaam,
                                k.eenmalige_korting_toegezegd, a.adres AS klantadres FROM Klant k
                         JOIN Adres a ON a.adres_id=k.betaaladres_id
                         WHERE k.klant_id=%s AND k.actief=TRUE""", (customer_id,))
            customer = c.fetchone()
            if not customer:
                raise DomainError("Unknown customer")
            c.execute("""SELECT 1 FROM Factuur WHERE klant_id=%s
                         AND incasso_ingeschakeld=TRUE AND betaald_op IS NULL
                         LIMIT 1""", (customer_id,))
            if c.fetchone():
                raise DomainError("Customer cannot order during active debt collection")
            c.execute("""
                SELECT COUNT(*) AS paid_count,
                       COUNT(f.totaal_bedrag) AS known_amount_count,
                       COALESCE(SUM(f.totaal_bedrag),0) AS annual
                FROM Factuur AS f
                WHERE f.klant_id=%s AND f.betaald_op>= %s AND f.betaald_op< %s
            """, (customer_id, date(year,1,1), date(year+1,1,1)))
            result = c.fetchone()
            if result["paid_count"] != result["known_amount_count"]:
                raise DomainError(
                    "De netto betaalde jaaromzet is niet betrouwbaar vastgelegd voor alle facturen."
                )
            return customer, result["annual"]

    def customer_order_count(self, customer_id):
        with self.db.cursor() as c:
            c.execute("SELECT COUNT(*) FROM Bestelling WHERE klant_id=%s", (customer_id,))
            return c.fetchone()[0]

    def invoice_for_customer(self, customer_id):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""
                SELECT f.factuur_id, f.factuurdatum, f.betaald_op, f.week_start,
                       f.afzenderadres, f.factuuradres, f.betalingsregeling_geaccepteerd,
                       f.incasso_ingeschakeld,
                       f.extra_bezorgkosten_excl_btw, f.extra_bezorgkosten_btw,
                       f.extra_bezorgkosten_incl_btw,
                       f.bedrag_excl_btw,
                       f.btw_bedrag,
                       f.bedrag_incl_btw,
                       f.bestellingskorting,
                       f.bedrag_na_bestellingskorting,
                       f.eenmalige_korting,
                       f.bedrag_na_eenmalige_korting,
                       f.klantenkorting,
                       f.totaal_bedrag,
                       k.bedrijfsnaam, a.adres
                FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id
                JOIN Adres a ON a.adres_id=k.betaaladres_id
WHERE f.klant_id=%s AND f.betaald_op IS NULL
                ORDER BY f.factuurdatum DESC
            """, (customer_id,))
            invoices=c.fetchall()
            for invoice in invoices:
                c.execute("""
                    SELECT l.aantal_geleverd AS quantity, b.prijs_per_eenheid AS unit_price
                    FROM Leveringregel l JOIN Levering v ON v.levering_id=l.levering_id
                    JOIN Bestelregel b ON b.bestelling_id=v.bestelling_id AND b.product_id=l.product_id
                    WHERE l.factuur_id=%s
                """, (invoice["factuur_id"],))
                invoice["lines"]=c.fetchall()
            return invoices

    def delivery_schedule(self, day):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""
                SELECT lp.levering_id, lp.pogingnummer, lp.geplande_tijd, lp.resultaat,
                       b.bestelling_id, b.status_naam, b.spoed,
                       k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                       ko.koerier_id, ko.naam AS koerier,
                       a.adres, r.ritdatum
                FROM Leverpoging lp
                JOIN Rit r ON r.rit_id=lp.rit_id
                JOIN Koerier ko ON ko.koerier_id=r.koerier_id
                JOIN Levering l ON l.levering_id=lp.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                JOIN Klant k ON k.klant_id=b.klant_id
                JOIN Adres a ON a.adres_id=b.afleveradres_id
                WHERE r.ritdatum=%s ORDER BY b.spoed DESC, lp.geplande_tijd, lp.levering_id
            """,(day,))
            return c.fetchall()

    @staticmethod
    def time_from_database(value):
        """MySQL TIME is represented as timedelta by mysql-connector-python."""
        if isinstance(value, timedelta):
            seconds = value.total_seconds()
            if seconds < 0 or seconds >= 86400 or seconds != int(seconds):
                raise DomainError("Ongeldige geplande bezorgtijd.")
            hours, remaining = divmod(int(seconds), 3600)
            minutes, seconds = divmod(remaining, 60)
            return time(hours, minutes, seconds)
        return value

    def register_delivery_attempt(self, delivery_id, delivery_date, delivered, attempt_time,
                                  receipt_signed=False):
        """Record the result of an already scheduled second visit, not a new visit."""
        self._validate_receipt(delivered, receipt_signed)
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT lp.rit_id, lp.pogingnummer, lp.resultaat, lp.geplande_tijd
                       FROM Leverpoging AS lp
                       JOIN Rit AS r ON r.rit_id = lp.rit_id
                       WHERE lp.levering_id = %s AND r.ritdatum = %s
                       ORDER BY lp.pogingnummer DESC LIMIT 1 FOR UPDATE""",
                    (delivery_id, delivery_date),
                )
                attempt = cursor.fetchone()
                if not attempt or attempt["pogingnummer"] != 2:
                    raise DomainError("Plan eerst de tweede poging na een mislukte eerste poging.")
                if attempt["resultaat"] is not None:
                    raise DomainError("Tweede bezorgpoging is al geregistreerd.")
                planned_time = self.time_from_database(attempt["geplande_tijd"])
                if attempt_time is not None and attempt_time != planned_time:
                    raise DomainError("De bezorgpoging hoort bij een ander gepland tijdstip.")
                cursor.execute(
                    """UPDATE Leverpoging
                       SET resultaat = %s, ontvangst_getekend = %s
                       WHERE levering_id = %s AND pogingnummer = 2
                         AND resultaat IS NULL""",
                    ("afgeleverd" if delivered else "niet aanwezig",
                     receipt_signed, delivery_id),
                )
                if cursor.rowcount != 1:
                    raise DomainError("De tweede bezorgpoging is al verwerkt.")
                if delivered:
                    self._record_delivered_lines(cursor, delivery_id)
                    self._mark_order_after_delivery(cursor, delivery_id)
                else:
                    cursor.execute(
                        """UPDATE Bestelling AS b
                           JOIN Levering AS l ON l.bestelling_id = b.bestelling_id
                           SET b.status_naam = 'niet afgeleverd'
                           WHERE l.levering_id = %s""",
                        (delivery_id,),
                    )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def register_first_delivery_attempt(self, delivery_id, delivery_date, delivered,
                                        receipt_signed=False, second_time=None):
        """Schedule the return trip immediately when the first delivery failed."""
        self._validate_receipt(delivered, receipt_signed)
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT lp.resultaat, lp.geplande_tijd, lp.rit_id
                       FROM Leverpoging AS lp
                       JOIN Rit AS r ON r.rit_id = lp.rit_id
                       WHERE lp.levering_id = %s AND lp.pogingnummer = 1
                         AND r.ritdatum = %s FOR UPDATE""",
                    (delivery_id, delivery_date),
                )
                attempt = cursor.fetchone()
                if attempt is None:
                    raise DomainError("Eerste bezorgpoging niet gevonden.")
                if attempt["resultaat"] is not None:
                    raise DomainError("Eerste bezorgpoging is al geregistreerd.")
                if not delivered:
                    planned_time = self.time_from_database(attempt["geplande_tijd"])
                    if (not isinstance(second_time, time)
                            or second_time <= planned_time
                            or second_time >= time(18, 0)):
                        raise DomainError(
                            "Plan de tweede poging later op dezelfde dag, vóór 18:00 uur."
                        )
                cursor.execute(
                    """UPDATE Leverpoging
                       SET resultaat = %s, ontvangst_getekend = %s
                       WHERE levering_id = %s AND pogingnummer = 1 AND resultaat IS NULL""",
                    ("afgeleverd" if delivered else "niet aanwezig",
                     receipt_signed, delivery_id),
                )
                if cursor.rowcount != 1:
                    raise DomainError("Eerste bezorgpoging is al geregistreerd.")
                if delivered:
                    self._record_delivered_lines(cursor, delivery_id)
                    self._mark_order_after_delivery(cursor, delivery_id)
                else:
                    cursor.execute(
                        """INSERT INTO Leverpoging
                           (levering_id, pogingnummer, rit_id, geplande_tijd,
                            resultaat, ontvangst_getekend)
                           VALUES (%s, 2, %s, %s, NULL, FALSE)""",
                        (delivery_id, attempt["rit_id"], second_time),
                    )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _validate_receipt(delivered, receipt_signed):
        if delivered and not receipt_signed:
            raise DomainError("De klant moet voor ontvangst hebben getekend.")
        if receipt_signed and not delivered:
            raise DomainError("Een niet-afgeleverde bestelling kan niet zijn ondertekend.")

    @staticmethod
    def _record_delivered_lines(cursor, delivery_id):
        cursor.execute(
            """INSERT INTO Leveringregel
                   (levering_id, product_id, aantal_geleverd, factuur_id)
               SELECT l.levering_id, dr.product_id, SUM(dr.aantal), NULL
               FROM Levering AS l
               JOIN Deelorder AS d ON d.bestelling_id = l.bestelling_id
                                   AND d.afgerond = TRUE
               JOIN Deelorderregel AS dr ON dr.deelorder_id = d.deelorder_id
               WHERE l.levering_id = %s
               GROUP BY l.levering_id, dr.product_id""",
            (delivery_id,),
        )
        if cursor.rowcount == 0:
            raise DomainError("Er zijn geen verzamelde producten om als geleverd vast te leggen.")

    @staticmethod
    def _mark_order_after_delivery(cursor, delivery_id):
        """Count all signed deliveries before marking an order fully delivered."""
        # A partial signed shipment must not change 'verstuurd' into a
        # fictional 'afgeleverd'; an existing recorded backorder remains one.
        # The original case uses a recorded status, never infers a new one.
        cursor.execute(MARK_ORDER_DELIVERED_IF_COMPLETE, (delivery_id,))

    def record_first_attempt_delivery(self, delivery_id, delivery_day, signature_confirmed):
        """Confirm a pre-packed first delivery without inventing a new delivery line.

        The distribution preparation flow has already recorded the packed
        medicines in Leveringregel. Only the signed receipt is new here.
        """
        if signature_confirmed != "yes":
            raise DomainError("Bevestig dat de klant heeft getekend voor ontvangst.")
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT lp.resultaat
                       FROM Leverpoging AS lp
                       JOIN Rit AS r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=%s AND lp.pogingnummer=1
                         AND r.ritdatum=%s FOR UPDATE""",
                    (delivery_id, delivery_day),
                )
                attempt=cursor.fetchone()
                if attempt is None:
                    raise DomainError("Eerste bezorgpoging niet gevonden.")
                if attempt["resultaat"] is not None:
                    raise DomainError("Eerste bezorgpoging is al verwerkt.")
                cursor.execute(
                    "SELECT COUNT(*) AS lines FROM Leveringregel WHERE levering_id=%s",
                    (delivery_id,),
                )
                if not cursor.fetchone()["lines"]:
                    raise DomainError("Er zijn geen ingepakte medicijnen om af te leveren.")
                cursor.execute(
                    """UPDATE Leverpoging SET resultaat='afgeleverd',
                              ontvangst_getekend=TRUE
                       WHERE levering_id=%s AND pogingnummer=1
                         AND resultaat IS NULL""",
                    (delivery_id,),
                )
                if cursor.rowcount != 1:
                    raise DomainError("De bezorgpoging is ondertussen verwerkt.")
                self._mark_order_after_delivery(cursor, delivery_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def record_second_attempt_outcome(self, delivery_id, delivery_day, outcome, signature_confirmed):
        """Record second visit only after it takes place; never invent a signature."""
        if outcome not in ("afgeleverd", "niet aanwezig"):
            raise DomainError("Ongeldige afleveruitkomst.")
        if outcome == "afgeleverd" and signature_confirmed != "yes":
            raise DomainError("Bevestig dat de klant voor ontvangst heeft getekend.")
        if outcome == "niet aanwezig" and signature_confirmed == "yes":
            raise DomainError("Zonder aflevering kan geen ontvangst worden bevestigd.")
        with self.db.cursor(dictionary=True) as c:
            try:
                c.execute(
                    """SELECT lp.resultaat FROM Leverpoging lp
                       JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=%s AND lp.pogingnummer=2 AND r.ritdatum=%s
                       FOR UPDATE""",
                    (delivery_id, delivery_day),
                )
                row = c.fetchone()
                if not row:
                    raise DomainError("Geen tweede bezorgpoging gepland voor deze dag.")
                if row["resultaat"] is not None:
                    raise DomainError("Tweede bezorgpoging is al afgehandeld.")
                c.execute(
                    """UPDATE Leverpoging SET resultaat=%s, ontvangst_getekend=%s
                       WHERE levering_id=%s AND pogingnummer=2""",
                    (outcome, outcome == "afgeleverd", delivery_id),
                )
                if outcome == "afgeleverd":
                    self._mark_order_after_delivery(c, delivery_id)
                else:
                    c.execute(
                        """UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
                           SET b.status_naam='niet afgeleverd' WHERE l.levering_id=%s""",
                        (delivery_id,),
                    )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def record_failed_delivery_followup(self, delivery_id, requested_date,
                                        time_slot, extra_cost, explanation):
        """Sales agrees a new delivery time and explains extra costs after two absences."""
        from decimal import Decimal, InvalidOperation
        if time_slot not in ("ochtend", "middag"):
            raise DomainError("Kies ochtend of middag als levermoment.")
        if not isinstance(requested_date, date):
            raise DomainError("Een nieuwe leverdatum is verplicht.")
        try:
            cost = Decimal(str(extra_cost))
        except (InvalidOperation, TypeError, ValueError) as exc:
            raise DomainError("Bezorgkosten moeten een geldig bedrag zijn.") from exc
        if not cost.is_finite() or cost < 0 or cost.as_tuple().exponent < -2:
            raise DomainError("Bezorgkosten moeten een niet-negatief bedrag in eurocent zijn.")
        if cost > 0 and not explanation.strip():
            raise DomainError("Leg extra bezorgkosten kort uit.")
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT b.bestelling_id, r.ritdatum FROM Bestelling b
                       JOIN Levering l ON l.bestelling_id=b.bestelling_id
                       JOIN Leverpoging lp ON lp.levering_id=l.levering_id AND lp.pogingnummer=2
                       JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE l.levering_id=%s AND lp.resultaat='niet aanwezig'
                       FOR UPDATE""", (delivery_id,))
                row = cursor.fetchone()
                if row is None:
                    raise DomainError("Er zijn geen twee mislukte bezorgpogingen geregistreerd.")
                if requested_date <= row["ritdatum"]:
                    raise DomainError("Plan een nieuwe leverdag na de mislukte bezorgdag.")
                cursor.execute(
                    """UPDATE Bestelling SET gewenste_leverdatum=%s, dagdeel=%s,
                       extra_bezorgkosten=%s, toelichting_extra_bezorgkosten=%s
                       WHERE bestelling_id=%s
                         AND extra_bezorgkosten_factuur_id IS NULL""",
                    (requested_date, time_slot, cost, explanation.strip() or None,
                     row["bestelling_id"]))
                if cursor.rowcount != 1:
                    raise DomainError("Deze bezorgkosten zijn al gefactureerd.")
                # The second absence closes this shipment. The agreed next
                # attempt is a NEW shipment, preserving the previous attempts.
                # Move its unbilled packed lines without duplicating quantities.
                cursor.execute(
                    "INSERT INTO Levering(bestelling_id) VALUES(%s)",
                    (row["bestelling_id"],),
                )
                new_delivery_id = cursor.lastrowid
                cursor.execute(
                    """UPDATE Leveringregel SET levering_id=%s
                       WHERE levering_id=%s AND factuur_id IS NULL""",
                    (new_delivery_id, delivery_id),
                )
                if cursor.rowcount < 1:
                    raise DomainError("Geen ongefactureerde producten voor de nieuwe leverpoging.")
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def prospect_followups(self, cutoff):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""
                SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
                       p.contactgegevens, a.adres, p.klant_id,
                       MAX(v.bezoekdatum) AS bezoekdatum
                FROM PotentieleKlant p JOIN Acquisitiebezoek v ON v.potentiele_klant_id=p.potentiele_klant_id
                JOIN Adres a ON a.adres_id=p.adres_id
                WHERE p.opvolging_afgesloten=FALSE AND NOT EXISTS (
                    SELECT 1 FROM Bestelling b WHERE b.klant_id = p.klant_id
                )
                GROUP BY p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,p.contactgegevens,a.adres,p.klant_id
                HAVING MAX(v.bezoekdatum)<=%s
                ORDER BY bezoekdatum
            """,(cutoff,))
            return c.fetchall()

    def record_visit(self, company, contact, details, address, visited):
        with self.db.cursor() as c:
            try:
                c.execute("INSERT INTO Adres (adres) VALUES (%s)",(address,))
                addr=c.lastrowid
                c.execute("INSERT INTO PotentieleKlant (bedrijfsnaam,contactpersoon,contactgegevens,adres_id) VALUES (%s,%s,%s,%s)",(company,contact,details,addr))
                prospect=c.lastrowid
                c.execute("INSERT INTO Acquisitiebezoek (potentiele_klant_id,bezoekdatum) VALUES (%s,%s)",(prospect,visited))
                self.db.commit()
                return prospect
            except Exception:
                self.db.rollback()
                raise

    def register_prospect_customer(self, prospect, billing, delivery):
        with self.db.cursor(dictionary=True) as c:
            try:
                c.execute("SELECT * FROM PotentieleKlant WHERE potentiele_klant_id=%s FOR UPDATE",(prospect,))
                p=c.fetchone()
                if not p or p["klant_id"] is not None or p["opvolging_afgesloten"]:
                    raise DomainError("Deze acquisitieopvolging is al afgesloten of geconverteerd.")
                from domain.business import ProspectiveCustomer
                c.execute(
                    "SELECT MAX(bezoekdatum) AS laatste_bezoek FROM Acquisitiebezoek "
                    "WHERE potentiele_klant_id=%s", (prospect,))
                last_visit = c.fetchone()
                if not last_visit or not last_visit["laatste_bezoek"] or not (
                    ProspectiveCustomer(p["bedrijfsnaam"]).checkFollowUpAfterOneMonth(
                        last_visit["laatste_bezoek"], date.today()
                    )
                ):
                    raise DomainError("De opvolging is pas een maand na het bezoek toegestaan.")
                c.execute("INSERT INTO Adres (adres) VALUES (%s)",(billing,))
                billing_id=c.lastrowid
                c.execute("INSERT INTO Adres (adres) VALUES (%s)",(delivery,))
                delivery_id=c.lastrowid
                c.execute("""INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id,eenmalige_korting_toegezegd)
                             VALUES(%s,%s,%s,%s,%s,TRUE)""",(p["bedrijfsnaam"],p["contactgegevens"],p["contactpersoon"],delivery_id,billing_id))
                customer=c.lastrowid
                c.execute("UPDATE PotentieleKlant SET klant_id=%s, opvolging_afgesloten=TRUE WHERE potentiele_klant_id=%s",(customer,prospect))
                self.db.commit()
                return customer
            except Exception:
                self.db.rollback()
                raise

    def close_prospect_followup(self, prospect_id, cutoff):
        """A definitive no after the callback ends acquisition; do not contact again."""
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT klant_id, opvolging_afgesloten FROM PotentieleKlant "
                    "WHERE potentiele_klant_id=%s FOR UPDATE", (prospect_id,))
                prospect = cursor.fetchone()
                if prospect is None or prospect["opvolging_afgesloten"]:
                    raise DomainError("Deze opvolging bestaat niet of is al afgesloten.")
                cursor.execute(
                    "SELECT MAX(bezoekdatum) AS laatste_bezoek FROM Acquisitiebezoek "
                    "WHERE potentiele_klant_id=%s", (prospect_id,))
                visited = cursor.fetchone()
                if not visited or not visited["laatste_bezoek"] or visited["laatste_bezoek"] > cutoff:
                    raise DomainError("Opvolging mag pas een maand na het bezoek worden afgesloten.")
                if prospect["klant_id"] is not None:
                    cursor.execute("SELECT COUNT(*) AS aantal FROM Bestelling WHERE klant_id=%s",
                                   (prospect["klant_id"],))
                    if cursor.fetchone()["aantal"]:
                        raise DomainError("Deze apotheek heeft al besteld; opvolging is niet nodig.")
                cursor.execute(
                    "UPDATE PotentieleKlant SET opvolging_afgesloten=TRUE "
                    "WHERE potentiele_klant_id=%s", (prospect_id,))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def record_payment_action(self, invoice_id, action, today):
        """Record the case's reminders, full payment, or rejected plan/debt collection."""
        with self.db.cursor(dictionary=True) as cursor:
            try:
                cursor.execute(
                    "SELECT f.factuur_id,f.klant_id,f.factuurdatum,f.betaald_op "
                    "FROM Factuur f WHERE f.factuur_id=%s FOR UPDATE", (invoice_id,))
                invoice=cursor.fetchone()
                if not invoice:
                    raise DomainError("Invoice not found")
                if action in ("reminder1", "reminder2"):
                    if invoice["betaald_op"]:
                        raise DomainError("Paid invoices need no reminder")
                    sequence=1 if action=="reminder1" else 2
                    min_days=sequence*7
                    if (today-invoice["factuurdatum"]).days<min_days:
                        raise DomainError("Reminder is not due")
                    cursor.execute(
                        "SELECT verstuurd_op FROM Betalingsherinnering "
                        "WHERE factuur_id=%s AND volgnummer=%s", (invoice_id, sequence))
                    if cursor.fetchone():
                        raise DomainError("Deze herinnering is al geregistreerd.")
                    if sequence==2:
                        cursor.execute(
                            "SELECT verstuurd_op FROM Betalingsherinnering "
                            "WHERE factuur_id=%s AND volgnummer=1", (invoice_id,))
                        first = cursor.fetchone()
                        if not first:
                            raise DomainError("Registreer eerst de eerste herinnering.")
                        if (today - first["verstuurd_op"]).days < 7:
                            raise DomainError("De tweede herinnering volgt pas minimaal een week later.")
                    cursor.execute(
                        "INSERT INTO Betalingsherinnering(factuur_id,volgnummer,verstuurd_op) "
                        "VALUES(%s,%s,%s)", (invoice_id,sequence,today))
                elif action=="payment_plan_accepted":
                    if invoice["betaald_op"] or (today-invoice["factuurdatum"]).days<21:
                        raise DomainError("Een betalingsregeling volgt pas na drie onbetaalde weken.")
                    cursor.execute(
                        "UPDATE Factuur SET betalingsregeling_geaccepteerd=TRUE WHERE factuur_id=%s",
                        (invoice_id,))
                elif action=="payment_plan_rejected":
                    if invoice["betaald_op"] or (today-invoice["factuurdatum"]).days<21:
                        raise DomainError("Debt collection can start only after three unpaid weeks")
                    cursor.execute(
                        "UPDATE Factuur SET betalingsregeling_geaccepteerd=FALSE, "
                        "incasso_ingeschakeld=TRUE WHERE factuur_id=%s", (invoice_id,))
                elif action=="mark_paid":
                    if invoice["betaald_op"]:
                        raise DomainError("Factuur is al betaald; betaaldatum mag niet worden overschreven.")
                    cursor.execute("UPDATE Factuur SET betaald_op=%s WHERE factuur_id=%s",
                                   (today,invoice_id))
                else:
                    raise DomainError("Unsupported invoice action")
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def save_invoice_snapshot(self, invoice_id, invoice_data, commit=True):
        """Store the issued invoice amounts once, not recomputed at payment time."""
        from domain.business import euro
        values = tuple(euro(invoice_data[field]) for _, field in [('bedrag_excl_btw', 'total_ex_vat'), ('btw_bedrag', 'vat_9_percent'), ('bedrag_incl_btw', 'total_incl_vat'), ('bestellingskorting', 'order_discount'), ('bedrag_na_bestellingskorting', 'total_after_order_discount'), ('eenmalige_korting', 'first_order_discount'), ('bedrag_na_eenmalige_korting', 'total_after_first_order_discount'), ('klantenkorting', 'customer_discount'), ('totaal_bedrag', 'total')])
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT factuur_id, totaal_bedrag FROM Factuur WHERE factuur_id=%s FOR UPDATE",
                    (invoice_id,),
                )
                current = cursor.fetchone()
                if current is None:
                    raise DomainError("Factuur niet gevonden.")
                if current["totaal_bedrag"] is not None:
                    raise DomainError("Het factuurbedrag is al definitief vastgelegd.")
                cursor.execute(
                    """UPDATE Factuur SET bedrag_excl_btw=%s, btw_bedrag=%s, bedrag_incl_btw=%s, bestellingskorting=%s, bedrag_na_bestellingskorting=%s, eenmalige_korting=%s, bedrag_na_eenmalige_korting=%s, klantenkorting=%s, totaal_bedrag=%s WHERE factuur_id=%s""",
                    values + (invoice_id,),
                )
            if commit:
                self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def determine_annual_customer_discounts(self, as_of=None):
        """On December 31, fix next year's discount for every customer (AD28).

        Only fully paid invoices count. The snapshot cannot be reissued after
        it is fixed. Every customer is processed in one transaction.
        """
        from services.discount_service import DiscountService

        as_of = as_of or date.today()
        if (as_of.month, as_of.day) != (12, 31):
            raise DomainError("De jaarlijkse klantkorting wordt op 31 december vastgesteld.")
        next_year = as_of.year + 1
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT klant_id FROM Klant ORDER BY klant_id FOR UPDATE")
                customers = cursor.fetchall()
                cursor.execute(
                    "SELECT COUNT(*) AS aantal FROM Klantkorting WHERE kalenderjaar=%s",
                    (next_year,),
                )
                if cursor.fetchone()["aantal"]:
                    raise ConflictError(
                        "De klantkortingen voor volgend jaar zijn al vastgesteld."
                    )
                for customer in customers:
                    customer_id = customer["klant_id"]
                    cursor.execute(
                        """SELECT COUNT(*) AS paid_count,
                                  COUNT(totaal_bedrag) AS known_count,
                                  COALESCE(SUM(totaal_bedrag), 0) AS jaaromzet
                           FROM Factuur
                           WHERE klant_id=%s AND betaald_op >= %s AND betaald_op <= %s""",
                        (customer_id, date(as_of.year, 1, 1), as_of),
                    )
                    revenue = cursor.fetchone()
                    if revenue["paid_count"] != revenue["known_count"]:
                        raise DomainError(
                            "Onvolledige betaalde factuurhistorie: bepaal geen korting op basis van geschatte omzet."
                        )
                    percentage = DiscountService.determine_discount_percentage(
                        revenue["jaaromzet"]
                    )
                    cursor.execute(
                        """INSERT INTO Klantkorting(klant_id, kalenderjaar, percentage)
                           VALUES (%s, %s, %s)""",
                        (customer_id, next_year, percentage),
                    )
            self.db.commit()
            return len(customers)
        except Exception:
            self.db.rollback()
            raise

    def uninvoiced_deliveries(self):
        """Overview required before the weekly invoice is approved."""
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT b.bestelling_id, k.klant_id, k.bedrijfsnaam,
                          MAX(r.ritdatum) AS afgeleverd_op,
                          SUM(lr.aantal_geleverd * br.prijs_per_eenheid) AS subtotaal,
                          b.extra_bezorgkosten
                   FROM Leveringregel AS lr
                   JOIN Levering AS l ON l.levering_id = lr.levering_id
                   JOIN Bestelling AS b ON b.bestelling_id = l.bestelling_id
                   JOIN Klant AS k ON k.klant_id = b.klant_id
                   JOIN Bestelregel AS br
                     ON br.bestelling_id = b.bestelling_id
                    AND br.product_id = lr.product_id
                   JOIN Leverpoging AS lp
                     ON lp.levering_id = lr.levering_id
                    AND lp.resultaat = 'afgeleverd'
                   JOIN Rit AS r ON r.rit_id = lp.rit_id
                   WHERE lr.factuur_id IS NULL
                   GROUP BY b.bestelling_id, k.klant_id, k.bedrijfsnaam,
                            b.extra_bezorgkosten
                   ORDER BY afgeleverd_op, k.bedrijfsnaam, b.bestelling_id"""
            )
            return cursor.fetchall()

    def outstanding_purchase_invoices(self):
        """List unpaid supplier invoices; receiving new stock is not implemented."""
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT i.inkoopfactuur_id, i.factuurdatum, i.bedrag,
                          l.naam AS leverancier
                   FROM Inkoopfactuur AS i
                   JOIN Leverancier AS l ON l.leverancier_id = i.leverancier_id
                   WHERE i.betaald_op IS NULL
                   ORDER BY i.factuurdatum, i.inkoopfactuur_id"""
            )
            return cursor.fetchall()

    def mark_purchase_invoice_paid(self, invoice_id, paid_on):
        """Only record a supplier invoice payment the employee has confirmed."""
        if invoice_id < 1:
            raise DomainError("Kies een geldig inkoopfactuurnummer.")
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT inkoopfactuur_id, betaald_op
                       FROM Inkoopfactuur WHERE inkoopfactuur_id=%s FOR UPDATE""",
                    (invoice_id,),
                )
                invoice = cursor.fetchone()
                if invoice is None:
                    raise NotFoundError("Inkoopfactuur niet gevonden.")
                if invoice["betaald_op"] is not None:
                    raise ConflictError("Deze inkoopfactuur is al betaald.")
                cursor.execute(
                    "UPDATE Inkoopfactuur SET betaald_op=%s WHERE inkoopfactuur_id=%s",
                    (paid_on, invoice_id),
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
