"""Database reads for the order-status overview and AD06 search/detail screen.

The case does not define a calculated backorder quantity. Order and line values
are retrieved as recorded; no estimated shortages or business statuses.
"""


class OrderStatusReportRepository:
    ORDER_SELECT = """
        SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
               b.gewenste_leverdatum, b.dagdeel, b.spoed, b.status_naam
        FROM Bestelling AS b
        JOIN Klant AS k ON k.klant_id = b.klant_id
    """

    def __init__(self, connection):
        self.connection = connection

    def list_orders(self):
        """Read all stored order statuses for management, newest first."""
        query = self.ORDER_SELECT + """
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def search_orders(self, term):
        """AD06: find orders by exact order number or partial customer name."""
        identifier = int(term) if term.isascii() and term.isdecimal() and len(term) <= 10 else None
        # A customer's literal '%' or '_' must not become a SQL LIKE wildcard.
        literal = term.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        query = self.ORDER_SELECT + """
            WHERE (b.bestelling_id = %s OR k.bedrijfsnaam LIKE %s ESCAPE '!')
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (identifier, f"%{literal}%"))
            return cursor.fetchall()

    def find_order(self, order_id):
        """Read a single stored order; includes delivery date and time slot."""
        query = self.ORDER_SELECT + """
            WHERE b.bestelling_id = %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchone()

    def list_order_lines(self, order_id):
        """Read ordered products and the customer's stored shortage choice.

        afnemen_bij_tekort is a customer choice, not a confirmed quantity
        missing from stock. No per-line backorder count is inferred.
        """
        query = """
            SELECT br.product_id, p.artikelnummer, p.productnaam,
                   br.aantal, br.prijs_per_eenheid, br.afnemen_bij_tekort
            FROM Bestelregel AS br
            JOIN Product AS p ON p.product_id = br.product_id
            WHERE br.bestelling_id = %s
            ORDER BY p.productnaam ASC, p.product_id ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()
