"""Repository for aisle-based robot assignments and sub-order completion."""

from domain.errors import ConflictError, NotFoundError


class RobotOrderRepository:
    def __init__(self, connection):
        self.connection = connection

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
        sql = """SELECT dr.product_id, p.productnaam, dr.aantal
                 FROM Deelorderregel AS dr
                 JOIN Product AS p ON p.product_id = dr.product_id
                 WHERE dr.deelorder_id = %s
                 ORDER BY p.productnaam, dr.product_id"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (suborder_id,))
            return cursor.fetchall()

    def complete(self, robot_id, suborder_id):
        """Complete only an unfinished sub-order belonging to this robot.

        Lock the row to make duplicate completion messages harmless but explicit.
        At least one registered physical bin is required before completion.
        """
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT deelorder_id, afgerond
                       FROM Deelorder WHERE deelorder_id = %s AND robot_id = %s
                       FOR UPDATE""",
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
                count = cursor.fetchone()["bin_count"]
                if not count:
                    raise ConflictError("Registreer eerst minimaal een verzamelbak.")
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
                    "SELECT bestelling_id FROM Bestelling WHERE bestelling_id = %s FOR UPDATE",
                    (order_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Bestelling niet gevonden.")
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
            self.connection.commit()
            return assignments
        except Exception:
            self.connection.rollback()
            raise
