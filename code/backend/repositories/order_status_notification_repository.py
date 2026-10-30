"""Read a customer order's status, delivery moment and order lines for the sales employee."""


class OrderStatusNotificationRepository:
    """Queries for looking up an order and informing the customer about its status."""

    def __init__(self, connection):
        self.connection = connection

    def search_orders(self, order_id, customer_name):
        """Find orders by exact order number or by part of the customer name, newest first.

        order_id is None when the search term is not a number, so only the name matches.
        """
        query = """
            SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
                   b.gewenste_leverdatum, b.dagdeel, b.status_naam
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            WHERE b.bestelling_id = %s OR k.bedrijfsnaam LIKE %s
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id, f"%{customer_name}%"))
            return cursor.fetchall()

    def find_order(self, order_id):
        """Return one order with its customer, delivery address and actual delivery date.

        afgeleverd_op is the trip date of the successful delivery attempt, or None.
        """
        query = """
            SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum, b.dagdeel,
                   b.status_naam, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                   a.adres AS afleveradres, l.afgeleverd_op
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            JOIN Adres AS a ON a.adres_id = b.afleveradres_id
            LEFT JOIN (
                SELECT lv.bestelling_id, MAX(r.ritdatum) AS afgeleverd_op
                FROM Levering AS lv
                JOIN Leverpoging AS lp ON lp.levering_id = lv.levering_id
                JOIN Rit AS r ON r.rit_id = lp.rit_id
                WHERE lp.resultaat = 'afgeleverd'
                GROUP BY lv.bestelling_id
            ) AS l ON l.bestelling_id = b.bestelling_id
            WHERE b.bestelling_id = %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchone()

    def find_order_lines(self, order_id):
        """Return the order lines with the quantity already reserved from stock."""
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam, br.aantal,
                   COALESCE(vr.aantal, 0) AS gereserveerd
            FROM Bestelregel AS br
            JOIN Product AS p ON p.product_id = br.product_id
            LEFT JOIN Voorraadreservering AS vr
                   ON vr.bestelling_id = br.bestelling_id
                  AND vr.product_id = br.product_id
            WHERE br.bestelling_id = %s
            ORDER BY p.productnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()
