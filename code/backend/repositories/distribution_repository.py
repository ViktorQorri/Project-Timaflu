"""Database access for the distribution corner and order packing."""

from datetime import datetime, timedelta
from decimal import Decimal

from domain.errors import ConflictError, NotFoundError


ORDERS_WITH_BINS_QUERY = """
    SELECT b.bestelling_id, b.status_naam, b.spoed, b.gewenste_leverdatum,
           b.dagdeel, b.aantal_verhuisdozen, k.bedrijfsnaam,
           af.adres AS afleveradres, d.deelorder_id, d.afgerond,
           v.unieke_code, r.gang
    FROM Bestelling AS b
    JOIN Klant AS k ON k.klant_id = b.klant_id
    JOIN Adres AS af ON af.adres_id = b.afleveradres_id
    JOIN Deelorder AS d ON d.bestelling_id = b.bestelling_id
    LEFT JOIN Verzamelbak AS v ON v.deelorder_id = d.deelorder_id
    LEFT JOIN Robot AS r ON r.robot_id = d.robot_id
    WHERE b.status_naam NOT IN ('verstuurd', 'afgeleverd')
      AND EXISTS (
          SELECT 1 FROM Deelorder AS d2
          JOIN Verzamelbak AS v2 ON v2.deelorder_id = d2.deelorder_id
          WHERE d2.bestelling_id = b.bestelling_id
      )
    ORDER BY b.bestelling_id DESC, d.deelorder_id ASC, v.unieke_code ASC
"""


class DistributionRepository:
    def __init__(self, connection):
        """Create a repository that uses the request's database connection.

        Args:
            connection: An open MySQL connection.
        """
        self.connection = connection

    def list_orders_with_bins(self):
        """Return order, sub-order and collection-bin rows for the distribution page.

        Returns:
            Rows ordered by customer order, sub-order and bin code.
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(ORDERS_WITH_BINS_QUERY)
            return cursor.fetchall()

    def packing_label(self, order_id):
        """Address label for a packed order, including the emergency marker."""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT b.bestelling_id, b.spoed, b.aantal_verhuisdozen,
                          k.bedrijfsnaam, k.telefoonnummer, a.adres AS afleveradres
                   FROM Bestelling AS b
                   JOIN Klant AS k ON k.klant_id = b.klant_id
                   JOIN Adres AS a ON a.adres_id = b.afleveradres_id
                   WHERE b.bestelling_id = %s""",
                (order_id,),
            )
            label = cursor.fetchone()
        if label is None:
            raise NotFoundError("Bestelling niet gevonden.")
        if label["aantal_verhuisdozen"] < 1:
            raise ConflictError("Registreer eerst de verpakking van deze bestelling.")
        return label

    def list_order_lines(self, order_id):
        """Return the product lines that belong to a customer order.

        Args:
            order_id: The order whose contents are shown while packing.

        Returns:
            Product lines ordered by product name.
        """
        query = """
            SELECT p.artikelnummer, p.productnaam, br.aantal, br.afnemen_bij_tekort
            FROM Bestelregel AS br
            JOIN Product AS p ON p.product_id = br.product_id
            WHERE br.bestelling_id = %s
            ORDER BY p.productnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()

    def list_orders_to_schedule(self):
        """Return released orders that do not yet have a delivery schedule."""
        query = """
            SELECT b.bestelling_id, b.gewenste_leverdatum, b.dagdeel, b.spoed,
                   k.bedrijfsnaam, k.telefoonnummer, a.adres AS afleveradres
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            JOIN Adres AS a ON a.adres_id = b.afleveradres_id
            WHERE b.status_naam = 'verstuurd'
              -- Rebooking is allowed only when every earlier delivery failed twice.
              AND NOT EXISTS (
                  SELECT 1 FROM Levering AS l
                  LEFT JOIN Leverpoging AS retry
                    ON retry.levering_id = l.levering_id AND retry.pogingnummer = 2
                  WHERE l.bestelling_id = b.bestelling_id
                    AND (retry.resultaat IS NULL OR retry.resultaat <> 'niet aanwezig')
              )
              -- Never create another delivery for the same scheduled date.
              AND NOT EXISTS (
                  SELECT 1 FROM Levering AS l
                  JOIN Leverpoging AS lp ON lp.levering_id = l.levering_id
                  JOIN Rit AS r ON r.rit_id = lp.rit_id
                  WHERE l.bestelling_id = b.bestelling_id
                    AND r.ritdatum = b.gewenste_leverdatum
              )
            ORDER BY b.spoed DESC, b.gewenste_leverdatum, b.bestelling_id
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def list_couriers(self):
        """Return couriers and their manually managed availability."""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                """SELECT koerier_id, naam, beschikbaar
                   FROM Koerier
                   ORDER BY naam, koerier_id"""
            )
            return cursor.fetchall()

    def create_courier(self, name):
        """Add a courier as unavailable until staff confirms availability."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Koerier (naam, beschikbaar) VALUES (%s, FALSE)",
                    (name,),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def set_courier_availability(self, courier_id, available):
        """Update a courier's availability after locking its row."""
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT koerier_id FROM Koerier WHERE koerier_id = %s FOR UPDATE",
                    (courier_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Koerier niet gevonden.")
                cursor.execute(
                    "UPDATE Koerier SET beschikbaar = %s WHERE koerier_id = %s",
                    (available, courier_id),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def schedule_delivery(self, order_id, courier_id, planned_time, region_confirmed=None):
        """Create a delivery and first attempt for a released order."""
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT status_naam, gewenste_leverdatum, spoed, besteld_op
                       FROM Bestelling
                       WHERE bestelling_id = %s
                       FOR UPDATE""",
                    (order_id,),
                )
                order = cursor.fetchone()
                if order is None:
                    raise NotFoundError("Bestelling niet gevonden.")
                if order["status_naam"] != "verstuurd":
                    raise ConflictError("Geef de bestelling eerst vrij voor distributie.")
                # The case defines three geographic regions but no address-to-
                # region boundaries. Therefore staff must confirm the matching
                # region for a non-urgent trip, without inventing a location map.
                if not order.get("spoed") and region_confirmed != "yes":
                    raise ConflictError("Controleer en bevestig de eigen koeriersregio van het afleveradres.")
                if order.get("spoed"):
                    planned_at = datetime.combine(order["gewenste_leverdatum"], planned_time)
                    ordered_at = order.get("besteld_op")
                    if (
                        ordered_at is None
                        or planned_at < ordered_at
                        or planned_at > ordered_at + timedelta(hours=3)
                    ):
                        raise ConflictError(
                            "Een spoedbestelling moet binnen drie uur na plaatsing worden afgeleverd."
                        )
                cursor.execute(
                    "SELECT levering_id FROM Levering WHERE bestelling_id = %s FOR UPDATE",
                    (order_id,),
                )
                if cursor.fetchall():
                    cursor.execute(
                        """SELECT lp.pogingnummer, lp.resultaat, r.ritdatum
                           FROM Levering AS l
                           JOIN Leverpoging AS lp ON lp.levering_id = l.levering_id
                           JOIN Rit AS r ON r.rit_id = lp.rit_id
                           WHERE l.bestelling_id = %s
                           ORDER BY l.levering_id DESC, lp.pogingnummer DESC
                           LIMIT 1 FOR UPDATE""",
                        (order_id,),
                    )
                    previous = cursor.fetchone()
                    if (previous is None
                            or previous["pogingnummer"] != 2
                            or previous["resultaat"] != "niet aanwezig"
                            or previous["ritdatum"] >= order["gewenste_leverdatum"]):
                        raise ConflictError("Deze bestelling heeft al een actieve levering.")
                cursor.execute(
                    """SELECT koerier_id, beschikbaar
                       FROM Koerier
                       WHERE koerier_id = %s
                       FOR UPDATE""",
                    (courier_id,),
                )
                courier = cursor.fetchone()
                if courier is None:
                    raise NotFoundError("Koerier niet gevonden.")
                if not courier["beschikbaar"]:
                    raise ConflictError("Kies een koerier die als beschikbaar staat geregistreerd.")
                cursor.execute(
                    """SELECT rit_id
                       FROM Rit
                       WHERE koerier_id = %s AND ritdatum = %s
                       FOR UPDATE""",
                    (courier_id, order["gewenste_leverdatum"]),
                )
                ride = cursor.fetchone()
                if ride is None:
                    cursor.execute(
                        "INSERT INTO Rit (koerier_id, ritdatum) VALUES (%s, %s)",
                        (courier_id, order["gewenste_leverdatum"]),
                    )
                    ride_id = cursor.lastrowid
                else:
                    ride_id = ride["rit_id"]
                cursor.execute(
                    "INSERT INTO Levering (bestelling_id) VALUES (%s)",
                    (order_id,),
                )
                delivery_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Leverpoging
                           (levering_id, pogingnummer, rit_id, geplande_tijd)
                       VALUES (%s, 1, %s, %s)""",
                    (delivery_id, ride_id, planned_time),
                )
            self.connection.commit()
            return order["gewenste_leverdatum"]
        except Exception:
            self.connection.rollback()
            raise

    def reschedule_failed_delivery(
        self, delivery_id, new_date, part_of_day, extra_cost, explanation,
    ):
        """Keep the two failed attempts, and update the existing order after contact."""
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT b.bestelling_id, b.status_naam, b.gewenste_leverdatum,
                              b.extra_bezorgkosten, b.toelichting_extra_bezorgkosten
                       FROM Levering AS l
                       JOIN Bestelling AS b ON b.bestelling_id = l.bestelling_id
                       WHERE l.levering_id = %s FOR UPDATE""",
                    (delivery_id,),
                )
                order = cursor.fetchone()
                if order is None:
                    raise NotFoundError("Deze levering bestaat niet.")
                if order["status_naam"] != "niet afgeleverd":
                    raise ConflictError("De levering is niet tweemaal mislukt.")
                cursor.execute(
                    """SELECT lp.pogingnummer, lp.resultaat, r.ritdatum
                       FROM Leverpoging AS lp
                       JOIN Rit AS r ON r.rit_id = lp.rit_id
                       WHERE lp.levering_id = %s
                       ORDER BY lp.pogingnummer FOR UPDATE""",
                    (delivery_id,),
                )
                attempts = cursor.fetchall()
                if (len(attempts) != 2 or
                        [(a["pogingnummer"], a["resultaat"]) for a in attempts]
                        != [(1, "niet aanwezig"), (2, "niet aanwezig")]):
                    raise ConflictError("Registreer eerst beide mislukte bezorgpogingen.")
                old_date = attempts[0]["ritdatum"]
                if (attempts[1]["ritdatum"] != old_date
                        or order["gewenste_leverdatum"] != old_date
                        or new_date <= old_date):
                    raise ConflictError("De nieuwe afspraak moet na de mislukte levering liggen.")
                new_total = Decimal(order["extra_bezorgkosten"]) + extra_cost
                if new_total > Decimal("99999999.99"):
                    raise ConflictError("De totale extra bezorgkosten zijn te hoog.")
                prior = order["toelichting_extra_bezorgkosten"] or ""
                details = (prior + "; " if prior else "") + explanation
                if len(details) > 255:
                    raise ConflictError("De gecombineerde toelichting is te lang.")
                cursor.execute(
                    """UPDATE Bestelling
                       SET gewenste_leverdatum = %s, dagdeel = %s,
                           extra_bezorgkosten = %s,
                           toelichting_extra_bezorgkosten = %s,
                           status_naam = 'verstuurd'
                       WHERE bestelling_id = %s""",
                    (new_date, part_of_day, new_total, details,
                     order["bestelling_id"]),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def pack_order(self, order_id, box_count):
        """Record the box count and mark a completely picked order as packed.

        Args:
            order_id: The customer order to pack.
            box_count: Number of moving boxes used for the order.
        """
        connection = self.connection
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT bestelling_id, status_naam
                       FROM Bestelling
                       WHERE bestelling_id = %s
                       FOR UPDATE""",
                    (order_id,),
                )
                order = cursor.fetchone()
                if order is None:
                    raise NotFoundError("Bestelling niet gevonden.")
                if order["status_naam"] in {
                    "backorder",
                    "ingepakt",
                    "verstuurd",
                    "afgeleverd",
                }:
                    raise ConflictError("Deze bestelling kan niet meer worden verpakt.")

                cursor.execute(
                    """SELECT deelorder_id, afgerond
                       FROM Deelorder
                       WHERE bestelling_id = %s
                       FOR UPDATE""",
                    (order_id,),
                )
                sub_orders = cursor.fetchall()
                if not sub_orders or any(not sub_order["afgerond"] for sub_order in sub_orders):
                    raise ConflictError(
                        "Verpak de bestelling pas als alle deelorders zijn afgerond."
                    )

                cursor.execute(
                    """SELECT v.unieke_code
                       FROM Verzamelbak AS v
                       JOIN Deelorder AS d ON d.deelorder_id = v.deelorder_id
                       WHERE d.bestelling_id = %s
                       LIMIT 1""",
                    (order_id,),
                )
                if cursor.fetchone() is None:
                    raise ConflictError("Bij deze bestelling zijn geen verzamelbakken geregistreerd.")

                cursor.execute(
                    """UPDATE Bestelling
                       SET aantal_verhuisdozen = %s, status_naam = 'ingepakt'
                       WHERE bestelling_id = %s""",
                    (box_count, order_id),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def release_order(self, order_id):
        """Release a packed order for distribution in one transaction.

        Args:
            order_id: The packed customer order to release.
        """
        connection = self.connection
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT status_naam, aantal_verhuisdozen
                       FROM Bestelling
                       WHERE bestelling_id = %s
                       FOR UPDATE""",
                    (order_id,),
                )
                order = cursor.fetchone()
                if order is None:
                    raise NotFoundError("Bestelling niet gevonden.")
                if order["status_naam"] != "ingepakt" or order["aantal_verhuisdozen"] < 1:
                    raise ConflictError("Verpak de bestelling voordat je deze vrijgeeft.")
                cursor.execute(
                    """UPDATE Bestelling SET status_naam = 'verstuurd'
                       WHERE bestelling_id = %s""",
                    (order_id,),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
