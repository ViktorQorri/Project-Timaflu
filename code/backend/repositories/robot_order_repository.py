"""Repository for aisle-based robot assignments and sub-order completion."""

from domain.errors import ConflictError, NotFoundError


class RobotOrderRepository:
    def __init__(self, connection):
        self.connection = connection

    def orders_ready_for_dispatch(self):
        """Return new orders with reserved stock that have no generated sub-orders."""
        sql = """
            SELECT b.bestelling_id, k.bedrijfsnaam, b.gewenste_leverdatum,
                   b.dagdeel, b.spoed
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            WHERE b.status_naam IN ('nieuw', 'wordt verzameld', 'backorder')
              AND EXISTS (
                  SELECT 1 FROM Voorraadreservering AS vr
                  WHERE vr.bestelling_id = b.bestelling_id
              )
              AND NOT EXISTS (
                  SELECT 1 FROM Deelorder AS d
                  WHERE d.bestelling_id = b.bestelling_id
              )
            ORDER BY b.spoed DESC, b.gewenste_leverdatum ASC, b.bestelling_id ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def robot_for_aisle(self, robot_id, aisle):
        sql = "SELECT robot_id, gang FROM Robot WHERE robot_id = %s AND gang = %s"
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (robot_id, aisle))
            return cursor.fetchone()

    def next_suborder(self, robot_id):
        sql = """SELECT deelorder_id, bestelling_id
                 FROM Deelorder
                 WHERE robot_id = %s AND afgerond = FALSE
                 ORDER BY deelorder_id ASC LIMIT 1"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (robot_id,))
            return cursor.fetchone()

    def suborder_lines(self, suborder_id):
        """Give the robot product quantities and actual shelf locations in its aisle."""
        sql = """SELECT dr.product_id, p.productnaam, dr.aantal,
                        GROUP_CONCAT(CONCAT(m.gang, m.schapnummer)
                          ORDER BY m.schapnummer SEPARATOR ', ') AS magazijnlocaties
                 FROM Deelorderregel AS dr
                 JOIN Product AS p ON p.product_id = dr.product_id
                 JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id
                 JOIN Robot AS r ON r.robot_id = d.robot_id
                 LEFT JOIN Magazijnlocatie AS m
                   ON m.product_id = dr.product_id AND m.gang = r.gang
                      AND m.aantal > 0
                 WHERE dr.deelorder_id = %s
                 GROUP BY dr.product_id, p.productnaam, dr.aantal
                 ORDER BY p.productnaam, dr.product_id"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (suborder_id,))
            return cursor.fetchall()

    def complete(self, robot_id, suborder_id):
        """Finish a robot's picked items and update warehouse stock atomically.

        Picking removes medicines from physical shelves. Releasing the corresponding
        reservation prevents counting those units twice as unavailable.
        """
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT d.deelorder_id, d.bestelling_id, d.afgerond, r.gang
                       FROM Deelorder AS d
                       JOIN Robot AS r ON r.robot_id = d.robot_id
                       WHERE d.deelorder_id = %s AND d.robot_id = %s FOR UPDATE""",
                    (suborder_id, robot_id),
                )
                suborder = cursor.fetchone()
                if not suborder:
                    raise NotFoundError("Deelorder niet gevonden voor deze robot.")
                if suborder["afgerond"]:
                    raise ConflictError("Deelorder is al afgerond.")
                cursor.execute(
                    "SELECT COUNT(*) AS bin_count FROM Verzamelbak WHERE deelorder_id = %s",
                    (suborder_id,),
                )
                if not cursor.fetchone()["bin_count"]:
                    raise ConflictError("Registreer eerst minimaal een verzamelbak.")
                cursor.execute(
                    """SELECT product_id, aantal FROM Deelorderregel
                       WHERE deelorder_id = %s ORDER BY product_id""",
                    (suborder_id,),
                )
                lines = cursor.fetchall()
                if not lines:
                    raise ConflictError("Deelorder zonder regels kan niet worden afgerond.")

                for line in lines:
                    product_id = line["product_id"]
                    remaining = int(line["aantal"])
                    cursor.execute(
                        "SELECT product_id FROM Product WHERE product_id = %s FOR UPDATE",
                        (product_id,),
                    )
                    if cursor.fetchone() is None:
                        raise NotFoundError("Het verzamelde product bestaat niet.")
                    cursor.execute(
                        """SELECT schapnummer, aantal FROM Magazijnlocatie
                           WHERE product_id = %s AND gang = %s
                           ORDER BY schapnummer FOR UPDATE""",
                        (product_id, suborder["gang"]),
                    )
                    for location in cursor.fetchall():
                        take = min(remaining, int(location["aantal"]))
                        if take:
                            cursor.execute(
                                """UPDATE Magazijnlocatie SET aantal = aantal - %s
                                   WHERE gang = %s AND schapnummer = %s AND aantal >= %s""",
                                (take, suborder["gang"], location["schapnummer"], take),
                            )
                            if cursor.rowcount != 1:
                                raise ConflictError("De voorraad is tijdens het verzamelen gewijzigd.")
                            remaining -= take
                        if remaining == 0:
                            break
                    if remaining:
                        raise ConflictError("Onvoldoende voorraad in de toegewezen robotgang.")

                    cursor.execute(
                        """SELECT aantal FROM Voorraadreservering
                           WHERE bestelling_id = %s AND product_id = %s FOR UPDATE""",
                        (suborder["bestelling_id"], product_id),
                    )
                    reservation = cursor.fetchone()
                    if reservation is None or int(reservation["aantal"]) < line["aantal"]:
                        raise ConflictError("De gereserveerde voorraad komt niet overeen met de deelorder.")
                    if int(reservation["aantal"]) == line["aantal"]:
                        cursor.execute(
                            """DELETE FROM Voorraadreservering
                               WHERE bestelling_id = %s AND product_id = %s""",
                            (suborder["bestelling_id"], product_id),
                        )
                    else:
                        cursor.execute(
                            """UPDATE Voorraadreservering SET aantal = aantal - %s
                               WHERE bestelling_id = %s AND product_id = %s""",
                            (line["aantal"], suborder["bestelling_id"], product_id),
                        )
                cursor.execute(
                    "UPDATE Deelorder SET afgerond = TRUE WHERE deelorder_id = %s",
                    (suborder_id,),
                )
            self.connection.commit()
            return {"deelorder_id": suborder_id, "afgerond": True}
        except Exception:
            self.connection.rollback()
            raise

    def generate(self, order_id):
        """Split reserved order quantities by aisle in one transaction.

        Existing sub-orders and previously assigned quantities are accounted
        for before creating new rows, so an aisle cannot be assigned more
        than its recorded physical inventory.
        """
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT bestelling_id, status_naam
                       FROM Bestelling WHERE bestelling_id = %s FOR UPDATE""",
                    (order_id,),
                )
                order = cursor.fetchone()
                if order is None:
                    raise NotFoundError("Bestelling niet gevonden.")
                if order["status_naam"] not in {"nieuw", "wordt verzameld", "backorder"}:
                    raise ConflictError("Deze bestelling kan niet meer worden verdeeld over robots.")
                cursor.execute(
                    "SELECT COUNT(*) AS assigned_count FROM Deelorder WHERE bestelling_id = %s",
                    (order_id,),
                )
                if cursor.fetchone()["assigned_count"]:
                    raise ConflictError("Deelorders zijn al gegenereerd.")
                cursor.execute(
                    """SELECT product_id, aantal
                       FROM Voorraadreservering
                       WHERE bestelling_id = %s ORDER BY product_id""",
                    (order_id,),
                )
                reserved = cursor.fetchall()
                if not reserved:
                    raise ConflictError("Geen gereserveerde voorraad voor deze bestelling.")

                per_robot = {}
                for reservation in reserved:
                    product_id = reservation["product_id"]
                    remaining = int(reservation["aantal"])
                    cursor.execute(
                        "SELECT product_id FROM Product WHERE product_id = %s FOR UPDATE",
                        (product_id,),
                    )
                    if cursor.fetchone() is None:
                        raise NotFoundError("Gereserveerd product bestaat niet.")
                    cursor.execute(
                        """SELECT r.robot_id, m.gang,
                                  SUM(m.aantal) AS physical_stock,
                                  COALESCE((
                                    SELECT SUM(dr.aantal)
                                    FROM Deelorderregel AS dr
                                    JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id
                                    WHERE dr.product_id = %s AND d.robot_id = r.robot_id
                                       AND d.afgerond = FALSE
                                  ), 0) AS already_assigned
                           FROM Magazijnlocatie AS m
                           JOIN Robot AS r ON r.gang = m.gang
                           WHERE m.product_id = %s
                           GROUP BY r.robot_id, m.gang
                           ORDER BY m.gang, r.robot_id""",
                        (product_id, product_id),
                    )
                    for location in cursor.fetchall():
                        if remaining == 0:
                            break
                        available = max(0, int(location["physical_stock"]) -
                                        int(location["already_assigned"]))
                        take = min(remaining, available)
                        if take:
                            per_robot.setdefault(location["robot_id"], []).append(
                                {"product_id": product_id, "aantal": take}
                            )
                            remaining -= take
                    if remaining:
                        raise ConflictError(
                            "Onvoldoende vrij toewijsbare voorraad per robotgang."
                        )
                assignments = []
                for robot_id in sorted(per_robot):
                    cursor.execute(
                        "INSERT INTO Deelorder (bestelling_id, robot_id) VALUES (%s, %s)",
                        (order_id, robot_id),
                    )
                    suborder_id = cursor.lastrowid
                    for line in per_robot[robot_id]:
                        cursor.execute(
                            """INSERT INTO Deelorderregel
                               (deelorder_id, product_id, aantal)
                               VALUES (%s, %s, %s)""",
                            (suborder_id, line["product_id"], line["aantal"]),
                        )
                    assignments.append(
                        {"robot_id": robot_id, "suborder_id": suborder_id,
                         "lines": per_robot[robot_id]}
                    )
                cursor.execute(
                    "UPDATE Bestelling SET status_naam = 'wordt verzameld' "
                    "WHERE bestelling_id = %s",
                    (order_id,),
                )
            self.connection.commit()
            return assignments
        except Exception:
            self.connection.rollback()
            raise
