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
