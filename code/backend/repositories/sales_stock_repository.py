"""Current physical stock lookup required for telephone sales."""

class SalesStockRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_products(self, search):
        """Find matching medicines with quantities from every warehouse location."""
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam,
                   COALESCE(m.voorraad, 0) AS voorraad,
                   COALESCE(r.gereserveerd, 0) AS gereserveerd,
                   GREATEST(COALESCE(m.voorraad, 0) -
                            COALESCE(r.gereserveerd, 0), 0) AS beschikbaar
            FROM Product AS p
            LEFT JOIN (
                SELECT product_id, SUM(aantal) AS voorraad
                FROM Magazijnlocatie GROUP BY product_id
            ) AS m ON m.product_id = p.product_id
            LEFT JOIN (
                SELECT product_id, SUM(aantal) AS gereserveerd
                FROM Voorraadreservering GROUP BY product_id
            ) AS r ON r.product_id = p.product_id
            WHERE p.productnaam LIKE %s OR p.artikelnummer LIKE %s
            ORDER BY p.productnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (f"%{search}%", f"%{search}%"))
            return cursor.fetchall()
