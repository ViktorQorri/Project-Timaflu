"""Atomic weekly invoice issuing from signed, actually delivered lines.

Uses one transaction per customer, with a customer row lock and a unique
(customer, week) constraint. Already issued invoice amounts are immutable.
"""
from datetime import date, timedelta
from decimal import Decimal
from domain.business import Invoice, euro
from domain.errors import DomainError
from repositories.assessed_repository import AssessedRepository


class WeeklyInvoiceRepository:
    def __init__(self, connection):
        self.db = connection

    @staticmethod
    def validate_week(week_start, issued_on, sender_address):
        if not isinstance(week_start, date) or week_start.weekday() != 0:
            raise DomainError("De factuurweek moet op maandag beginnen.")
        if week_start + timedelta(days=6) >= issued_on:
            raise DomainError("Factureer alleen een volledig afgesloten week.")
        if not sender_address or not sender_address.strip():
            raise DomainError(
                "Het werkelijke Timaflu-afzenderadres ontbreekt. "
                "Vul TIMAFLU_ADDRESS in voordat je facturen uitgeeft."
            )

    def eligible_customers(self, week_start):
        """One customer appears once even with multiple delivered lines."""
        week_end = week_start + timedelta(days=6)
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT DISTINCT b.klant_id
                FROM Leveringregel lr
                JOIN Levering l ON l.levering_id=lr.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                WHERE lr.factuur_id IS NULL
                  AND EXISTS (
                    SELECT 1 FROM Leverpoging lp
                    JOIN Rit r ON r.rit_id=lp.rit_id
                    WHERE lp.levering_id=l.levering_id
                      AND lp.resultaat='afgeleverd'
                      AND lp.ontvangst_getekend=TRUE
                      AND r.ritdatum BETWEEN %s AND %s
                  )
                ORDER BY b.klant_id
            """, (week_start, week_end))
            return [row["klant_id"] for row in cursor.fetchall()]

    def issue_week(self, week_start, sender_address, issued_on=None):
        """Issue each eligible customer once. Does not send email or invent an address."""
        issued_on = issued_on or date.today()
        self.validate_week(week_start, issued_on, sender_address)
        issued_ids = []
        for customer_id in self.eligible_customers(week_start):
            invoice_id = self._issue_customer(
                customer_id, week_start, sender_address.strip(), issued_on
            )
            if invoice_id is not None:
                issued_ids.append(invoice_id)
        return issued_ids

    def _issue_customer(self, customer_id, week_start, sender_address, issued_on):
        end = week_start + timedelta(days=6)
        with self.db.cursor(dictionary=True) as cursor:
            try:
                # Serialize invoice issuing per customer before checking for existing weeks.
                cursor.execute("""
                    SELECT k.bedrijfsnaam, a.adres AS factuuradres
                    FROM Klant k JOIN Adres a ON a.adres_id=k.betaaladres_id
                    WHERE k.klant_id=%s FOR UPDATE
                """, (customer_id,))
                customer = cursor.fetchone()
                if not customer:
                    raise DomainError("Klant niet gevonden.")

                cursor.execute("""
                    SELECT factuur_id FROM Factuur
                    WHERE klant_id=%s AND week_start=%s FOR UPDATE
                """, (customer_id, week_start))
                if cursor.fetchone():
                    # Idempotent: never recalculate a previously issued invoice.
                    self.db.rollback()
                    return None

                # Price comes from saved order lines, quantity from actual deliveries.
                # EXISTS avoids duplicate lines from joining multiple delivery attempts.
                cursor.execute("""
                    SELECT lr.levering_id, lr.product_id, lr.aantal_geleverd AS quantity,
                           br.prijs_per_eenheid AS unit_price, b.bestelling_id AS order_id,
                           b.besteld_op, b.eenmalige_korting_toegepast AS first_used,
                           (SELECT SUM(ordered.aantal * ordered.prijs_per_eenheid)
                            FROM Bestelregel AS ordered
                            WHERE ordered.bestelling_id=b.bestelling_id) AS full_order_ex_vat
                    FROM Leveringregel lr
                    JOIN Levering l ON l.levering_id=lr.levering_id
                    JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                    JOIN Bestelregel br ON br.bestelling_id=b.bestelling_id
                                      AND br.product_id=lr.product_id
                    WHERE b.klant_id=%s AND lr.factuur_id IS NULL
                      AND EXISTS (
                        SELECT 1 FROM Leverpoging lp
                        JOIN Rit r ON r.rit_id=lp.rit_id
                        WHERE lp.levering_id=l.levering_id
                          AND lp.resultaat='afgeleverd'
                          AND lp.ontvangst_getekend=TRUE
                          AND r.ritdatum BETWEEN %s AND %s
                      )
                    ORDER BY b.besteld_op,b.bestelling_id,lr.levering_id,lr.product_id
                    FOR UPDATE
                """, (customer_id, week_start, end))
                rows = cursor.fetchall()
                if not rows:
                    self.db.rollback()
                    return None

                year = end.year - 1
                cursor.execute("""
                    SELECT COUNT(*) AS paid_count,
                           COUNT(totaal_bedrag) AS known_amount_count,
                           COALESCE(SUM(totaal_bedrag),0) AS annual
                    FROM Factuur
                    WHERE klant_id=%s AND betaald_op >= %s AND betaald_op < %s
                """, (customer_id, date(year,1,1), date(year+1,1,1)))
                revenue = cursor.fetchone()
                if revenue["paid_count"] != revenue["known_amount_count"]:
                    raise DomainError("Betaalde historische facturen missen bedragen.")

                cursor.execute("""
                    SELECT bestelling_id FROM Bestelling WHERE klant_id=%s
                    ORDER BY besteld_op,bestelling_id LIMIT 1
                """, (customer_id,))
                first_order_id = cursor.fetchone()["bestelling_id"]

                orders = {}
                for row in rows:
                    order_id = row["order_id"]
                    if order_id not in orders:
                        orders[order_id] = {
                            "order_id": order_id,
                            # Alle leveringen van dezelfde eerste bestelling krijgen de
                            # eenmalige korting; nooit andere bestellingen.
                            "first_order": order_id == first_order_id,
                            "mark_first_used": order_id == first_order_id and not row["first_used"],
                            "order_total": euro(Decimal(str(row["full_order_ex_vat"])) * Decimal("1.09")),
                            "lines": []
                        }
                    orders[order_id]["lines"].append({
                        "quantity": row["quantity"], "unit_price": row["unit_price"]
                    })
                # One first-order discount, even if acquisition also offered 10%.
                invoice = Invoice(customer_id, "", issued_on).createWeeklyInvoiceForOrders(
                    customer["bedrijfsnaam"], customer["factuuradres"],
                    list(orders.values()), revenue["annual"]
                )

                cursor.execute("""
                    INSERT INTO Factuur
                    (klant_id,factuurdatum,week_start,afzenderadres,factuuradres)
                    VALUES (%s,%s,%s,%s,%s)
                """, (customer_id, issued_on, week_start,
                      sender_address, customer["factuuradres"]))
                invoice_id = cursor.lastrowid

                # Reuse the existing one-write snapshot method in this transaction.
                AssessedRepository(self.db).save_invoice_snapshot(
                    invoice_id, invoice, commit=False
                )

                for row in rows:
                    cursor.execute("""
                        UPDATE Leveringregel SET factuur_id=%s
                        WHERE levering_id=%s AND product_id=%s AND factuur_id IS NULL
                    """, (invoice_id, row["levering_id"], row["product_id"]))
                    if cursor.rowcount != 1:
                        raise DomainError("Factuurregel is intussen gewijzigd.")

                for order in orders.values():
                    if order["mark_first_used"]:
                        cursor.execute("""
                            UPDATE Bestelling
                            SET eenmalige_korting_toegepast=TRUE
                            WHERE bestelling_id=%s AND eenmalige_korting_toegepast=FALSE
                        """, (order["order_id"],))
                        if cursor.rowcount != 1:
                            raise DomainError("Eenmalige korting is al gebruikt.")
                self.db.commit()
                return invoice_id
            except Exception:
                self.db.rollback()
                raise

    def issued_invoice(self, invoice_id):
        """Retrieve a persisted invoice even after it has been paid."""
        with self.db.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT f.*, k.bedrijfsnaam,
                       COALESCE(f.factuuradres,a.adres) AS adres
                FROM Factuur f JOIN Klant k ON k.klant_id=f.klant_id
                JOIN Adres a ON a.adres_id=k.betaaladres_id
                WHERE f.factuur_id=%s
            """, (invoice_id,))
            invoice = cursor.fetchone()
            if not invoice:
                return None
            cursor.execute("""
                SELECT lr.aantal_geleverd AS quantity,
                       br.prijs_per_eenheid AS unit_price, b.bestelling_id AS order_id
                FROM Leveringregel lr
                JOIN Levering l ON l.levering_id=lr.levering_id
                JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                JOIN Bestelregel br ON br.bestelling_id=b.bestelling_id
                                  AND br.product_id=lr.product_id
                WHERE lr.factuur_id=%s
                ORDER BY b.bestelling_id, lr.product_id
            """, (invoice_id,))
            invoice["lines"] = cursor.fetchall()
            return invoice
