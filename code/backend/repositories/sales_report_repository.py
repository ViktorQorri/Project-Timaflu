"""Sales figures for the management reports, read from the recorded orders."""


class SalesReportRepository:
    """Queries for the sales report screen.

    Revenue is the sum of quantity times unit price of the order lines (Bestelregel)
    of orders placed in the period. Every method takes a half-open period:
    start is included, end is excluded, so end is the day after the last day.
    """

    def __init__(self, connection):
        self.connection = connection

    def revenue_per_customer(self, start, end):
        """Return revenue and number of orders per customer, highest revenue first."""
        query = """
            SELECT k.klant_id, k.bedrijfsnaam,
                   COUNT(DISTINCT b.bestelling_id) AS aantal_bestellingen,
                   SUM(r.aantal * r.prijs_per_eenheid) AS omzet
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
            WHERE b.besteld_op >= %s AND b.besteld_op < %s
            GROUP BY k.klant_id, k.bedrijfsnaam
            ORDER BY omzet DESC, k.bedrijfsnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (start, end))
            return cursor.fetchall()

    def revenue_per_period(self, date_format, start, end):
        """Return revenue and number of orders per period, oldest period first.

        date_format is a MySQL DATE_FORMAT pattern such as '%Y-%m' for months.
        Periods without orders are not returned.
        """
        query = """
            SELECT DATE_FORMAT(b.besteld_op, %s) AS periode,
                   COUNT(DISTINCT b.bestelling_id) AS aantal_bestellingen,
                   SUM(r.aantal * r.prijs_per_eenheid) AS omzet
            FROM Bestelling AS b
            JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
            WHERE b.besteld_op >= %s AND b.besteld_op < %s
            GROUP BY periode
            ORDER BY periode ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (date_format, start, end))
            return cursor.fetchall()

    def best_selling_products(self, start, end, limit):
        """Return the medicines with the most units sold, at most limit rows."""
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam,
                   SUM(r.aantal) AS aantal_verkocht,
                   SUM(r.aantal * r.prijs_per_eenheid) AS omzet
            FROM Bestelregel AS r
            JOIN Bestelling AS b ON b.bestelling_id = r.bestelling_id
            JOIN Product AS p ON p.product_id = r.product_id
            WHERE b.besteld_op >= %s AND b.besteld_op < %s
            GROUP BY p.product_id, p.artikelnummer, p.productnaam
            ORDER BY aantal_verkocht DESC, omzet DESC, p.productnaam ASC
            LIMIT %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (start, end, limit))
            return cursor.fetchall()
