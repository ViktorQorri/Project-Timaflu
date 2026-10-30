"""Customer orders with their current status, for the management report."""


class OrderStatusReportRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_orders(self, date_from, date_to):
        """Return orders placed in the period, newest first.

        A None bound means no limit on that side. date_to includes the whole day.
        LEFT JOIN keeps orders that have no order lines yet.
        """
        query = """
            SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
                   b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam,
                   COUNT(r.product_id) AS aantal_regels
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            LEFT JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
            WHERE (%s IS NULL OR b.besteld_op >= %s)
              AND (%s IS NULL OR b.besteld_op < %s + INTERVAL 1 DAY)
            GROUP BY b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
                     b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (date_from, date_from, date_to, date_to))
            return cursor.fetchall()
