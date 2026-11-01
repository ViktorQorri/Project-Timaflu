"""Order lookups and the once-a-year customer discount determination (AD28)."""

from decimal import Decimal

from domain.errors import ConflictError, DomainError


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
            WHERE actief = TRUE
            ORDER BY bedrijfsnaam ASC
        """)

    def find_customer(self, customer_id):
        """Return one customer, or None when the id is unknown."""
        return self._fetchone("""
            SELECT klant_id, bedrijfsnaam
            FROM Klant
            WHERE klant_id = %s AND actief = TRUE
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

    def get_customer_discount_percentage(self, customer_id, year):
        """Read the annual rate set for the order's calendar year, never recalculate it."""
        row = self._fetchone("""
            SELECT percentage FROM Klantkorting
            WHERE klant_id = %s AND kalenderjaar = %s
        """, (customer_id, year))
        return None if row is None else row["percentage"]

    def list_customer_ids(self):
        """All customers to process in the 31 December annual determination."""
        return [row["klant_id"] for row in self._fetchall(
            "SELECT klant_id FROM Klant ORDER BY klant_id"
        )]

    def save_annual_discounts(self, year, rates):
        """Record next-year percentages atomically, preserving already confirmed values."""
        try:
            with self.connection.cursor(dictionary=True) as cursor:
                for customer_id, percentage in rates:
                    cursor.execute(
                        """SELECT percentage FROM Klantkorting
                           WHERE klant_id = %s AND kalenderjaar = %s FOR UPDATE""",
                        (customer_id, year),
                    )
                    current = cursor.fetchone()
                    if current is not None:
                        if Decimal(current["percentage"]) != Decimal(percentage):
                            raise ConflictError(
                                f"De klantenkorting voor {year} is al anders vastgesteld."
                            )
                        continue
                    cursor.execute(
                        """INSERT INTO Klantkorting (klant_id, kalenderjaar, percentage)
                           VALUES (%s, %s, %s)""",
                        (customer_id, year, percentage),
                    )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

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
            raise DomainError("Betaalde jaaromzet is niet volledig vastgelegd.")
        return row["jaaromzet"]
