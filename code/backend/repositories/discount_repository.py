"""Customer, product and order history lookups for the order discount calculation (SD01)."""

from datetime import date

from domain.errors import DomainError


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
        """Return persisted net totals from paid invoices in the selected year."""
        row = self._fetchone("""
            SELECT COUNT(*) AS paid_count,
                   COUNT(f.totaal_bedrag) AS known_amount_count,
                   COALESCE(SUM(f.totaal_bedrag), 0) AS jaaromzet
            FROM Factuur AS f
            WHERE f.klant_id = %s
              AND f.betaald_op >= %s
              AND f.betaald_op < %s
        """, (customer_id, date(year, 1, 1), date(year + 1, 1, 1)))
        if row["paid_count"] != row["known_amount_count"]:
            raise DomainError(
                "De netto betaalde jaaromzet is niet betrouwbaar vastgelegd voor alle facturen."
            )
        return row["jaaromzet"]
