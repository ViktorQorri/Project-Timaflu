"""MySQL queries for the five assessed scenarios, using the existing case tables."""
from datetime import date
from domain.errors import DomainError


class AssessedRepository:
    def __init__(self, connection):
        self.db = connection

    def customer_revenue(self, customer_id, year):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""SELECT k.klant_id, k.bedrijfsnaam, a.adres AS klantadres FROM Klant k
                         JOIN Adres a ON a.adres_id=k.betaaladres_id
                         WHERE k.klant_id=%s""", (customer_id,))
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
                SELECT f.factuur_id, f.factuurdatum, f.betaald_op, f.betalingsregeling_geaccepteerd,
                       f.incasso_ingeschakeld,
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
                WHERE f.klant_id=%s ORDER BY f.factuurdatum DESC
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
                       b.bestelling_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                       a.adres, r.ritdatum
                FROM Leverpoging lp
                JOIN Rit r ON r.rit_id=lp.rit_id
                JOIN Levering l ON l.levering_id=lp.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                JOIN Klant k ON k.klant_id=b.klant_id
                JOIN Adres a ON a.adres_id=b.afleveradres_id
                WHERE r.ritdatum=%s ORDER BY lp.geplande_tijd
            """,(day,))
            return c.fetchall()

    def record_first_attempt_delivery(self, delivery_id, delivery_day, signature_confirmed):
        """Register a signed successful first visit without a second attempt."""
        if signature_confirmed != "yes":
            raise DomainError("Bevestig dat de klant voor ontvangst heeft getekend.")
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT lp.resultaat FROM Leverpoging lp
                       JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=%s AND lp.pogingnummer=1 AND r.ritdatum=%s
                       FOR UPDATE""", (delivery_id, delivery_day))
                row = cursor.fetchone()
                if row is None or row["resultaat"] is not None:
                    raise DomainError("De eerste bezorgpoging ontbreekt of is al afgehandeld.")
                cursor.execute(
                    """UPDATE Leverpoging SET resultaat='afgeleverd', ontvangst_getekend=TRUE
                       WHERE levering_id=%s AND pogingnummer=1""", (delivery_id,))
                cursor.execute(
                    """UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
                       SET b.status_naam='afgeleverd' WHERE l.levering_id=%s""",
                    (delivery_id,))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def schedule_second_attempt(self, delivery_id, planned_time, delivery_day):
        """First absence: reschedule for the same delivery date, without an outcome."""
        with self.db.cursor(dictionary=True) as c:
            try:
                c.execute(
                    """SELECT lp.rit_id, lp.pogingnummer, lp.resultaat
                       FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id
                       WHERE lp.levering_id=%s AND r.ritdatum=%s
                       ORDER BY lp.pogingnummer DESC FOR UPDATE""",
                    (delivery_id, delivery_day),
                )
                row = c.fetchone()
                if not row:
                    raise DomainError("Levering niet in het rooster voor deze datum.")
                if row["pogingnummer"] != 1 or row["resultaat"] is not None:
                    raise DomainError("Tweede bezorgpoging is al gepland of de bestelling is afgeleverd.")
                c.execute(
                    """UPDATE Leverpoging SET resultaat='niet aanwezig',
                              ontvangst_getekend=FALSE
                       WHERE levering_id=%s AND pogingnummer=1""",
                    (delivery_id,),
                )
                c.execute(
                    """INSERT INTO Leverpoging
                       (levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
                       VALUES (%s,2,%s,%s,NULL,NULL)""",
                    (delivery_id, row["rit_id"], planned_time),
                )
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
                    c.execute(
                        """UPDATE Bestelling b JOIN Levering l ON l.bestelling_id=b.bestelling_id
                           SET b.status_naam='afgeleverd' WHERE l.levering_id=%s""",
                        (delivery_id,),
                    )
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
                WHERE NOT EXISTS (
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
                if not p or p["klant_id"] is not None:
                    raise DomainError("Prospect not available for conversion")
                c.execute("INSERT INTO Adres (adres) VALUES (%s)",(billing,))
                billing_id=c.lastrowid
                c.execute("INSERT INTO Adres (adres) VALUES (%s)",(delivery,))
                delivery_id=c.lastrowid
                c.execute("""INSERT INTO Klant(bedrijfsnaam,telefoonnummer,contactpersoon,afleveradres_id,betaaladres_id)
                             VALUES(%s,%s,%s,%s,%s)""",(p["bedrijfsnaam"],p["contactgegevens"],p["contactpersoon"],delivery_id,billing_id))
                customer=c.lastrowid
                c.execute("UPDATE PotentieleKlant SET klant_id=%s WHERE potentiele_klant_id=%s",(customer,prospect))
                self.db.commit()
                return customer
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
                    if sequence==2:
                        cursor.execute("SELECT 1 FROM Betalingsherinnering WHERE factuur_id=%s AND volgnummer=1",(invoice_id,))
                        if not cursor.fetchone():
                            raise DomainError("First reminder must be recorded before second")
                    cursor.execute(
                        "INSERT INTO Betalingsherinnering(factuur_id,volgnummer,verstuurd_op) "
                        "VALUES(%s,%s,%s)", (invoice_id,sequence,today))
                elif action=="payment_plan_accepted":
                    if invoice["betaald_op"]:
                        raise DomainError("Invoice already paid")
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
                    cursor.execute("UPDATE Factuur SET betaald_op=%s WHERE factuur_id=%s",
                                   (today,invoice_id))
                else:
                    raise DomainError("Unsupported invoice action")
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def save_invoice_snapshot(self, invoice_id, invoice_data):
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
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
