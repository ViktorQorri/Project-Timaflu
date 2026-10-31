"""Picking bins (Verzamelbak) linked to a robot's sub-order, as shown in AD10 Register_collection_bin.

A bin has no location column: its location is the aisle of the robot that collects the
sub-order (Deelorder -> Robot.gang), so it is derived instead of stored twice.
"""
from mysql.connector import IntegrityError

from domain.errors import ConflictError, DomainError, NotFoundError


class PickingBinRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_bins(self):
        """Return every registered bin with its order, sub-order and aisle."""
        query = """
            SELECT v.unieke_code, v.deelorder_id, d.bestelling_id,
                   d.robot_id, r.gang, d.afgerond
            FROM Verzamelbak AS v
            JOIN Deelorder AS d ON d.deelorder_id = v.deelorder_id
            JOIN Robot AS r ON r.robot_id = d.robot_id
            ORDER BY d.bestelling_id ASC, v.deelorder_id ASC, v.unieke_code ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def register(self, bin_code, sub_order_id, aisle):
        """Link a scanned bin to an open sub-order in one transaction.

        The sub-order is locked first so it cannot be completed while the bin is linked.
        Rejects an unknown or completed sub-order, a bin scanned in another aisle,
        and a bin code that is already registered.
        """
        conn = self.connection
        try:
            with conn.cursor(dictionary=True) as cur:
                cur.execute(
                    """SELECT d.deelorder_id, d.bestelling_id, d.afgerond, r.gang
                       FROM Deelorder AS d
                       JOIN Robot AS r ON r.robot_id = d.robot_id
                       WHERE d.deelorder_id = %s
                       FOR UPDATE""",
                    (sub_order_id,),
                )
                sub_order = cur.fetchone()
                if sub_order is None:
                    raise NotFoundError(f"Deelorder {sub_order_id} bestaat niet.")
                if sub_order["afgerond"]:
                    raise ConflictError(
                        f"Deelorder {sub_order_id} is al afgerond. Koppel de bak aan een open deelorder."
                    )
                if sub_order["gang"] != aisle:
                    raise DomainError(
                        f"Deelorder {sub_order_id} wordt verzameld in gang {sub_order['gang'] or 'onbekend'}, "
                        f"niet in gang {aisle}."
                    )
                cur.execute(
                    "SELECT deelorder_id FROM Verzamelbak WHERE unieke_code = %s",
                    (bin_code,),
                )
                existing = cur.fetchone()
                if existing is not None:
                    raise ConflictError(
                        f"Verzamelbak {bin_code} is al geregistreerd bij deelorder {existing['deelorder_id']}."
                    )
                try:
                    cur.execute(
                        "INSERT INTO Verzamelbak (unieke_code, deelorder_id) VALUES (%s, %s)",
                        (bin_code, sub_order_id),
                    )
                except IntegrityError as error:
                    # Another robot registered the same code between the check and the insert.
                    raise ConflictError(f"Verzamelbak {bin_code} is al geregistreerd.") from error
            conn.commit()
            return {
                "unieke_code": bin_code,
                "deelorder_id": sub_order["deelorder_id"],
                "bestelling_id": sub_order["bestelling_id"],
                "gang": sub_order["gang"],
            }
        except Exception:
            conn.rollback()
            raise
