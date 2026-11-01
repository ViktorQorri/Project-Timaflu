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
            SELECT klant_id, bedrijfsnaam, eenmalige_korting_toegezegd
            FROM Klant
            ORDER BY bedrijfsnaam ASC
        """)

    def find_customer(self, customer_id):
        """Return one customer, or None when the id is unknown."""
        return self._fetchone("""
            SELECT klant_id, bedrijfsnaam, eenmalige_korting_toegezegd
            FROM Klant
            WHERE klant_id = %s
        """, (customer_id,))

    def list_products(self):
        """Return every catalog product with its price for the order line selection."""
        return self._fetchall("""
            SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking, minimale_bestelhoeveelheid
            FROM Product
            WHERE in_assortiment = TRUE
            ORDER BY productnaam ASC
        """)

    def find_product(self, product_id):
        """Return one catalog product with its price, or None when the id is unknown."""
        return self._fetchone("""
            SELECT product_id, artikelnummer, productnaam, prijs_per_grootverpakking, minimale_bestelhoeveelheid
            FROM Product
            WHERE product_id = %s AND in_assortiment = TRUE
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
        """Sum paid invoice amounts in the year, as recorded by administration."""
        row = self._fetchone("""
            SELECT COALESCE(SUM(f.totaal_bedrag), 0) AS jaaromzet,
                   COUNT(*) AS betaalde_facturen,
                   COUNT(f.totaal_bedrag) AS facturen_met_bedrag
            FROM Factuur AS f
            WHERE f.klant_id = %s AND YEAR(f.betaald_op) = %s
        """, (customer_id, year))
        if row["betaalde_facturen"] != row["facturen_met_bedrag"]:
            from domain.errors import DomainError
            raise DomainError("Betaalde jaaromzet is niet volledig vastgelegd.")
        return row["jaaromzet"]
