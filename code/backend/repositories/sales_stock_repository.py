"""Current physical stock lookup required for telephone sales."""

class SalesStockRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_products(self, search):
        """Find matching medicines with quantities from every warehouse location."""
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam,
                   COALESCE(SUM(m.aantal), 0) AS voorraad
            FROM Product AS p
            LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
            WHERE p.productnaam LIKE %s OR p.artikelnummer LIKE %s
            GROUP BY p.product_id, p.artikelnummer, p.productnaam
            ORDER BY p.productnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (f"%{search}%", f"%{search}%"))
            return cursor.fetchall()
