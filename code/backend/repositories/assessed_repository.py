"""MySQL queries for the five assessed scenarios, using the existing case tables."""
from datetime import date, timedelta
from domain.errors import ConflictError, DomainError, NotFoundError


class AssessedRepository:
    def __init__(self, connection):
        self.db = connection

    def customer_revenue(self, customer_id, year):
        with self.db.cursor(dictionary=True) as c:
            c.execute("SELECT klant_id, bedrijfsnaam FROM Klant WHERE klant_id=%s", (customer_id,))
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
                       b.bestelling_id, b.status_naam, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
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

    def register_delivery_attempt(self, delivery_id, delivery_date, delivered, attempt_time, receipt_signed=False):
        self._validate_receipt(delivered, receipt_signed)
        with self.db.cursor() as c:
            try:
                c.execute("""SELECT lp.rit_id, lp.pogingnummer, lp.resultaat
                             FROM Leverpoging lp JOIN Rit r ON r.rit_id=lp.rit_id
                             WHERE lp.levering_id=%s AND r.ritdatum=%s
                             ORDER BY lp.pogingnummer DESC FOR UPDATE""",
                          (delivery_id, delivery_date))
                last=c.fetchone()
                if not last:
                    raise DomainError("Delivery not scheduled")
                ride, attempt, previous_result=last
                if previous_result != "niet aanwezig":
                    raise DomainError("De eerste poging moet eerst als niet aanwezig geregistreerd zijn.")
                if attempt >= 2:
                    raise DomainError("Maximum two attempts")
                c.execute("UPDATE Leverpoging SET resultaat='niet aanwezig' WHERE levering_id=%s AND pogingnummer=%s",(delivery_id,attempt))
                c.execute("""INSERT INTO Leverpoging (levering_id,pogingnummer,rit_id,geplande_tijd,resultaat,ontvangst_getekend)
                             VALUES (%s,2,%s,%s,%s,%s)""",
                          (delivery_id,ride,attempt_time,"afgeleverd" if delivered else "niet aanwezig",receipt_signed))
                if delivered:
                    self._record_delivered_lines(c, delivery_id)
                    self._mark_order_after_delivery(c, delivery_id)
                else:
                    c.execute(
                        """UPDATE Bestelling AS b JOIN Levering AS l
                           ON l.bestelling_id = b.bestelling_id
                           SET b.status_naam = 'niet afgeleverd'
                           WHERE l.levering_id = %s""",
                        (delivery_id,),
                    )
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

    def register_first_delivery_attempt(self, delivery_id, delivery_date, delivered, receipt_signed=False):
        self._validate_receipt(delivered, receipt_signed)
        with self.db.cursor() as c:
            try:
                c.execute(
                    """SELECT lp.resultaat
                       FROM Leverpoging AS lp
                       JOIN Rit AS r ON r.rit_id = lp.rit_id
                       WHERE lp.levering_id = %s AND lp.pogingnummer = 1
                         AND r.ritdatum = %s
                       FOR UPDATE""",
                    (delivery_id, delivery_date),
                )
                attempt = c.fetchone()
                if attempt is None:
                    raise DomainError("Eerste bezorgpoging niet gevonden.")
                if attempt[0] is not None:
                    raise DomainError("Eerste bezorgpoging is al geregistreerd.")
                c.execute(
                    """UPDATE Leverpoging
                       SET resultaat = %s, ontvangst_getekend = %s
                       WHERE levering_id = %s AND pogingnummer = 1""",
                    ("afgeleverd" if delivered else "niet aanwezig", receipt_signed,
                     delivery_id),
                )
                if delivered:
                    self._record_delivered_lines(c, delivery_id)
                    self._mark_order_after_delivery(c, delivery_id)
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
        """An order stays in backorder when not all requested medicines arrived."""
        cursor.execute(
            """UPDATE Bestelling AS b
               JOIN Levering AS l ON l.bestelling_id = b.bestelling_id
               SET b.status_naam = CASE
                   WHEN EXISTS (
                       SELECT 1 FROM Bestelregel AS br
                       LEFT JOIN Leveringregel AS lr
                         ON lr.levering_id = l.levering_id
                        AND lr.product_id = br.product_id
                       WHERE br.bestelling_id = b.bestelling_id
                         AND COALESCE(lr.aantal_geleverd, 0) < br.aantal
                   ) THEN 'backorder' ELSE 'afgeleverd' END
               WHERE l.levering_id = %s""",
            (delivery_id,),
        )

    def prospect_followups(self, cutoff):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""
                SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
                       p.contactgegevens, a.adres, MAX(v.bezoekdatum) AS bezoekdatum
                FROM PotentieleKlant p JOIN Acquisitiebezoek v ON v.potentiele_klant_id=p.potentiele_klant_id
                JOIN Adres a ON a.adres_id=p.adres_id
                WHERE p.klant_id IS NULL
                GROUP BY p.potentiele_klant_id,p.bedrijfsnaam,p.contactpersoon,p.contactgegevens,a.adres
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

    def create_weekly_invoice(self, customer_id, week_start, invoice_date):
        """Issue one invoice for the customer's delivered, unbilled lines in a week."""
        from domain.business import Invoice
        from repositories.discount_repository import DiscountRepository

        week_end = week_start + timedelta(days=7)
        try:
            with self.db.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT k.klant_id, k.bedrijfsnaam, a.adres
                       FROM Klant AS k
                       JOIN Adres AS a ON a.adres_id = k.betaaladres_id
                       WHERE k.klant_id = %s
                       FOR UPDATE""",
                    (customer_id,),
                )
                customer = cursor.fetchone()
                if customer is None:
                    raise DomainError("Klant niet gevonden.")
                cursor.execute(
                    """SELECT lr.levering_id, lr.product_id, b.bestelling_id, b.besteld_op,
                              lr.aantal_geleverd AS quantity,
                              br.prijs_per_eenheid AS unit_price,
                              b.eenmalige_korting_toegepast,
                              CASE WHEN EXISTS (
                                  SELECT 1 FROM Levering AS earlier_l
                                  JOIN Leveringregel AS earlier_lr
                                    ON earlier_lr.levering_id = earlier_l.levering_id
                                  WHERE earlier_l.bestelling_id = b.bestelling_id
                                    AND earlier_lr.factuur_id IS NOT NULL
                              ) THEN 0 ELSE b.extra_bezorgkosten END AS extra_bezorgkosten,
                               (SELECT SUM(x.aantal * x.prijs_per_eenheid)
                                  FROM Bestelregel AS x
                                 WHERE x.bestelling_id = b.bestelling_id) AS besteld_ex_btw
                       FROM Leveringregel AS lr
                       JOIN Levering AS l ON l.levering_id = lr.levering_id
                       JOIN Bestelling AS b ON b.bestelling_id = l.bestelling_id
                       JOIN Bestelregel AS br
                         ON br.bestelling_id = b.bestelling_id
                        AND br.product_id = lr.product_id
                       WHERE b.klant_id = %s
                         AND lr.factuur_id IS NULL
                         AND EXISTS (
                             SELECT 1
                             FROM Leverpoging AS lp
                             JOIN Rit AS r ON r.rit_id = lp.rit_id
                             WHERE lp.levering_id = lr.levering_id
                               AND lp.resultaat = 'afgeleverd'
                               AND r.ritdatum >= %s AND r.ritdatum < %s
                         )
                       ORDER BY lr.levering_id, lr.product_id
                       FOR UPDATE""",
                    (customer_id, week_start, week_end),
                )
                lines = cursor.fetchall()
                if not lines:
                    raise DomainError(
                        "Geen afgeleverde, ongefactureerde producten voor deze klant en week."
                    )
                # First-order eligibility belongs to the original order, not to
                # whichever weekly invoice happens to be issued first.
                first_order = any(
                    bool(line["eenmalige_korting_toegepast"]) for line in lines
                )
                yearly_revenue = {}
                revenue_repository = DiscountRepository(self.db)
                for line in lines:
                    ordered_on = line.get("besteld_op") or invoice_date
                    order_year = ordered_on.year
                    if order_year not in yearly_revenue:
                        yearly_revenue[order_year] = revenue_repository.sum_purchases(
                            customer_id, order_year - 1
                        )
                    line["annual_revenue"] = yearly_revenue[order_year]
                annual_revenue = yearly_revenue.get(invoice_date.year, 0)
                cursor.execute(
                    "INSERT INTO Factuur (klant_id, factuurdatum) VALUES (%s, %s)",
                    (customer_id, invoice_date),
                )
                invoice_id = cursor.lastrowid
                invoice_data = Invoice(
                    customer_id, str(invoice_id), invoice_date
                ).createWeeklyInvoice(
                    customer["bedrijfsnaam"],
                    customer["adres"],
                    lines,
                    annual_revenue,
                    first_order,
                )
                for line in lines:
                    cursor.execute(
                        """UPDATE Leveringregel
                           SET factuur_id = %s
                           WHERE levering_id = %s AND product_id = %s
                             AND factuur_id IS NULL""",
                        (invoice_id, line["levering_id"], line["product_id"]),
                    )
                    if cursor.rowcount != 1:
                        raise DomainError(
                            "Een leveringsregel is ondertussen al gefactureerd."
                        )
            self.save_invoice_snapshot(invoice_id, invoice_data)
            return invoice_id
        except Exception:
            self.db.rollback()
            raise
