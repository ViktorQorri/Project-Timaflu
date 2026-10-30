"""Customer, product and order history lookups for the order discount calculation (SD01)."""


class DiscountRepository:
    def __init__(self, connection):
        self.connection = connection

    def _fetchall(self, query, params=()):
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def _fetchone(self, query, params):
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchone()

    def list_customers(self):
        """Return every customer for the selection list, ordered by company name."""
        return self._fetchall("""
            SELECT klant_id, bedrijfsnaam
            FROM Klant
            ORDER BY bedrijfsnaam ASC
        """)

    def find_customer(self, customer_id):
        """Return one customer, or None when the id is unknown."""
        return self._fetchone("""
            SELECT klant_id, bedrijfsnaam
            FROM Klant
            WHERE klant_id = %s
        """, (customer_id,))

    def list_products(self):
        """Return every catalog product with its price for the order line selection."""
        return self._fetchall("""
            SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking
            FROM Product
            ORDER BY productnaam ASC
        """)

    def find_product(self, product_id):
        """Return one catalog product with its price, or None when the id is unknown."""
        return self._fetchone("""
            SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking
            FROM Product
            WHERE product_id = %s
        """, (product_id,))

    def count_previous_orders(self, customer_id):
        """SD01 countPreviousOrders(customer): number of orders already placed."""
        row = self._fetchone("""
            SELECT COUNT(*) AS aantal_bestellingen
            FROM Bestelling
            WHERE klant_id = %s
        """, (customer_id,))
        return int(row["aantal_bestellingen"])

    def sum_purchases(self, customer_id, year):
        """SD01 sumPurchases(previousYear): order line value of all orders placed in that year."""
        row = self._fetchone("""
            SELECT COALESCE(SUM(r.aantal * r.prijs_per_eenheid), 0) AS jaaromzet
            FROM Bestelling AS b
            JOIN Bestelregel AS r ON r.bestelling_id = b.bestelling_id
            WHERE b.klant_id = %s AND YEAR(b.besteld_op) = %s
        """, (customer_id, year))
        return row["jaaromzet"]
