"""Read existing orders and their current status for the order report."""


class OrderStatusReportRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_orders(self):
        """Return all orders and their customer and delivery information."""
        query = """
            SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
                   b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()
