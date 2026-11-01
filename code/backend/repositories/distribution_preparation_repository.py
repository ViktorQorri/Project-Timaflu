"""Verzamelde robotbakken verpakken en de bestaande koeriersrit plannen.

Leveringregels zijn pas factureerbaar nadat een echte ondertekende aflevering
in Leverpoging is vastgelegd. De registratie is per order/product idempotent.
"""
from datetime import date, datetime, time, timedelta
from domain.errors import ConflictError, DomainError, NotFoundError


class DistributionPreparationRepository:
    def __init__(self, connection):
        self.db = connection

    def ready_to_pack(self):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""
                SELECT b.bestelling_id, k.bedrijfsnaam,
                       (SELECT COALESCE(SUM(dr.aantal),0)
                        FROM Deelorder d JOIN Deelorderregel dr ON dr.deelorder_id=d.deelorder_id
                        WHERE d.bestelling_id=b.bestelling_id AND d.afgerond=TRUE) AS collected,
                       (SELECT COALESCE(SUM(lr.aantal_geleverd),0)
                        FROM Levering l JOIN Leveringregel lr ON lr.levering_id=l.levering_id
                        WHERE l.bestelling_id=b.bestelling_id) AS prepared
                FROM Bestelling b JOIN Klant k ON k.klant_id=b.klant_id
                WHERE NOT EXISTS(SELECT 1 FROM Deelorder d
                                 WHERE d.bestelling_id=b.bestelling_id AND d.afgerond=FALSE)
                  AND EXISTS(SELECT 1 FROM Deelorder d WHERE d.bestelling_id=b.bestelling_id)
                ORDER BY b.bestelling_id
            """)
            return [r for r in c.fetchall() if int(r["collected"]) > int(r["prepared"])]

    def pack(self, order_id):
        try:
            with self.db.cursor(dictionary=True) as c:
                c.execute("SELECT bestelling_id FROM Bestelling WHERE bestelling_id=%s FOR UPDATE", (order_id,))
                if c.fetchone() is None:
                    raise NotFoundError("Bestelling niet gevonden.")
                c.execute("""SELECT COUNT(*) AS uncompleted FROM Deelorder
                             WHERE bestelling_id=%s AND afgerond=FALSE""", (order_id,))
                if c.fetchone()["uncompleted"]:
                    raise ConflictError("Wacht totdat alle huidige robotdeelorders zijn afgerond.")
                c.execute("""SELECT dr.product_id,SUM(dr.aantal) AS collected
                             FROM Deelorder d JOIN Deelorderregel dr
                               ON dr.deelorder_id=d.deelorder_id
                             WHERE d.bestelling_id=%s AND d.afgerond=TRUE
                             GROUP BY dr.product_id ORDER BY dr.product_id""", (order_id,))
                quantities = c.fetchall()
                if not quantities:
                    raise ConflictError("Er zijn geen daadwerkelijk verzamelde medicijnen.")
                c.execute("""SELECT lr.product_id, SUM(lr.aantal_geleverd) AS prepared
                             FROM Levering l JOIN Leveringregel lr ON lr.levering_id=l.levering_id
                             WHERE l.bestelling_id=%s GROUP BY lr.product_id""", (order_id,))
                prepared = {int(r["product_id"]): int(r["prepared"]) for r in c.fetchall()}
                new = []
                for q in quantities:
                    pid = int(q["product_id"])
                    unprepared = int(q["collected"]) - prepared.get(pid, 0)
                    if unprepared < 0:
                        raise ConflictError("Meer producten verpakt dan verzameld.")
                    if unprepared:
                        new.append((pid, unprepared))
                if not new:
                    raise ConflictError("Deze producten zijn al verpakt voor distributie.")
                c.execute("INSERT INTO Levering (bestelling_id) VALUES (%s)", (order_id,))
                delivery_id = c.lastrowid
                for pid, number in new:
                    c.execute("""INSERT INTO Leveringregel
                                 (levering_id, product_id, aantal_geleverd)
                                 VALUES (%s,%s,%s)""", (delivery_id, pid, number))
            self.db.commit()
            return delivery_id
        except Exception:
            self.db.rollback()
            raise

    def pending_shipments(self):
        with self.db.cursor(dictionary=True) as c:
            c.execute("""SELECT l.levering_id, b.bestelling_id, b.gewenste_leverdatum,
                                b.dagdeel, b.spoed, k.bedrijfsnaam, a.adres
                         FROM Levering l JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                         JOIN Klant k ON k.klant_id=b.klant_id
                         JOIN Adres a ON a.adres_id=b.afleveradres_id
                         WHERE NOT EXISTS (SELECT 1 FROM Leverpoging lp
                                           WHERE lp.levering_id=l.levering_id)
                         ORDER BY b.spoed DESC, b.gewenste_leverdatum, l.levering_id""")
            deliveries = c.fetchall()
            c.execute("SELECT koerier_id,naam FROM Koerier WHERE beschikbaar=TRUE ORDER BY naam")
            couriers = c.fetchall()
        return deliveries, couriers

    def schedule(self, delivery_id, courier_id, scheduled_date, planned_time):
        """One confirmed courier assignment; do not invent a geographic region."""
        if (not isinstance(scheduled_date, date) or not isinstance(planned_time, time)
                or delivery_id < 1 or courier_id < 1):
            raise DomainError("Kies een geldig levermoment en een beschikbare koerier.")
        try:
            with self.db.cursor(dictionary=True) as c:
                c.execute("""SELECT b.bestelling_id,b.gewenste_leverdatum,b.dagdeel,
                                    b.spoed,b.besteld_op,b.status_naam
                             FROM Levering l JOIN Bestelling b ON b.bestelling_id=l.bestelling_id
                             WHERE l.levering_id=%s FOR UPDATE""", (delivery_id,))
                order = c.fetchone()
                if not order:
                    raise NotFoundError("Te plannen levering niet gevonden.")
                if scheduled_date != order["gewenste_leverdatum"]:
                    raise ConflictError("Plan op de met de klant afgesproken datum.")
                # Current-processes.md (Bestellingen): first delivery of a rush
                # order must be within three hours of its actual placement.
                # A newly negotiated delivery after two failed visits is separate.
                if order["spoed"] and order["status_naam"] != "niet afgeleverd":
                    scheduled_at = datetime.combine(scheduled_date, planned_time)
                    ordered_at = order["besteld_op"]
                    if not (ordered_at <= scheduled_at <= ordered_at + timedelta(hours=3)):
                        raise DomainError(
                            "Plan een spoedlevering vanaf de orderplaatsing en uiterlijk "
                            "drie uur daarna. Controleer de afgesproken koeriersrit."
                        )
                if ((planned_time.hour < 12) != (order["dagdeel"] == "ochtend")):
                    raise DomainError("Leveringstijd en gekozen dagdeel komen niet overeen.")
                c.execute("SELECT beschikbaar FROM Koerier WHERE koerier_id=%s FOR UPDATE",
                          (courier_id,))
                courier = c.fetchone()
                if not courier or not courier["beschikbaar"]:
                    raise ConflictError("De gekozen koerier is niet beschikbaar.")
                c.execute("SELECT COUNT(*) AS attempts FROM Leverpoging WHERE levering_id=%s",
                          (delivery_id,))
                if c.fetchone()["attempts"]:
                    raise ConflictError("Deze levering staat al in een koeriersrooster.")
                c.execute("""SELECT rit_id FROM Rit WHERE koerier_id=%s AND ritdatum=%s
                             ORDER BY rit_id LIMIT 1 FOR UPDATE""", (courier_id, scheduled_date))
                route = c.fetchone()
                if route:
                    ride_id = route["rit_id"]
                else:
                    c.execute("INSERT INTO Rit(koerier_id,ritdatum) VALUES(%s,%s)",
                              (courier_id, scheduled_date))
                    ride_id = c.lastrowid
                c.execute("""INSERT INTO Leverpoging
                             (levering_id,pogingnummer,rit_id,geplande_tijd)
                             VALUES (%s,1,%s,%s)""", (delivery_id, ride_id, planned_time))
                c.execute("UPDATE Bestelling SET status_naam='verstuurd' WHERE bestelling_id=%s",
                          (order["bestelling_id"],))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
