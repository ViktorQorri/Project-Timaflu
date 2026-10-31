"""Database access for the distribution corner and order packing."""

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
    WHERE (b.status_naam IS NULL OR b.status_naam NOT IN ('verstuurd', 'afgeleverd'))
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
