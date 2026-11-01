"""Reservation lifecycle operations for confirmed customer order lines.

Each product is locked first so simultaneous orders cannot reserve the same units.
These methods do not create customer orders; they are called after confirmation.
"""
from domain.errors import ConflictError, NotFoundError


class ReservationRepository:
    def __init__(self, connection):
        self.connection = connection

    def reserve_existing_line(self, order_id, product_id):
        """Reserve a confirmed order line in one transaction; reject shortages."""
        conn = self.connection
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT product_id FROM Product WHERE product_id = %s FOR UPDATE",
                    (product_id,),
                )
                if cur.fetchone() is None:
                    raise NotFoundError("Product niet gevonden.")
                cur.execute(
                    """SELECT aantal FROM Bestelregel
                       WHERE bestelling_id = %s AND product_id = %s""",
                    (order_id, product_id),
                )
                line = cur.fetchone()
                if line is None:
                    raise NotFoundError("Bestelregel niet gevonden.")
                quantity = int(line[0])
                cur.execute(
                    """SELECT aantal FROM Voorraadreservering
                       WHERE bestelling_id = %s AND product_id = %s""",
                    (order_id, product_id),
                )
                if cur.fetchone() is not None:
                    raise ConflictError("Deze bestelregel is al gereserveerd.")
                cur.execute(
                    "SELECT COALESCE(SUM(aantal), 0) FROM Magazijnlocatie WHERE product_id = %s",
                    (product_id,),
                )
                physical = int(cur.fetchone()[0])
                cur.execute(
                    "SELECT COALESCE(SUM(aantal), 0) FROM Voorraadreservering WHERE product_id = %s",
                    (product_id,),
                )
                reserved = int(cur.fetchone()[0])
                if quantity > physical - reserved:
                    raise ConflictError("Onvoldoende beschikbare voorraad voor deze bestelregel.")
                cur.execute(
                    """INSERT INTO Voorraadreservering (bestelling_id, product_id, aantal)
                       VALUES (%s, %s, %s)""",
                    (order_id, product_id, quantity),
                )
            conn.commit()
            return quantity
        except Exception:
            conn.rollback()
            raise

    def release_existing_line(self, order_id, product_id):
        """Release a reservation when an order line is cancelled or fulfilled."""
        conn = self.connection
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT product_id FROM Product WHERE product_id = %s FOR UPDATE",
                    (product_id,),
                )
                if cur.fetchone() is None:
                    raise NotFoundError("Product niet gevonden.")
                cur.execute(
                    """DELETE FROM Voorraadreservering
                       WHERE bestelling_id = %s AND product_id = %s""",
                    (order_id, product_id),
                )
                removed = cur.rowcount
            conn.commit()
            return removed > 0
        except Exception:
            conn.rollback()
            raise
