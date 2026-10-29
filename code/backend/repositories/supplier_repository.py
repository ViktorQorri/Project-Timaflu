"""Supplier offers for a medicine, using the current purchasing data."""

class SupplierRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_offers(self, product_name):
        """Find matching products and their offers, cheapest supplier first."""
        query = """
            SELECT p.product_id, p.productnaam, l.naam AS leverancier,
                   l.contactpersoon, l.telefoonnummer, a.inkoopprijs
            FROM Product AS p
            JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id
            JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id
            WHERE p.productnaam LIKE %s
            ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (f"%{product_name}%",))
            return cursor.fetchall()
