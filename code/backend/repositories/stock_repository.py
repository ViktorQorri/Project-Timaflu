"""Read the current physical inventory from the warehouse locations."""


class StockRepository:
    """Queries for the stock shortage dashboard."""

    def __init__(self, connection):
        self.connection = connection

    def list_stock_below_minimum(self):
        """Return products with physical inventory below their minimum.

        LEFT JOIN includes catalog products without any warehouse location.
        Products removed from the assortment are not reordered, so they are left out.
        All quantities use the same units as Magazijnlocatie.aantal.
        """
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam,
                   p.minimumvoorraad,
                   COALESCE(SUM(m.aantal), 0) AS voorraad
            FROM Product AS p
            LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
            WHERE p.in_assortiment = TRUE
            GROUP BY p.product_id, p.artikelnummer, p.productnaam,
                     p.minimumvoorraad
            HAVING voorraad < p.minimumvoorraad
            ORDER BY (p.minimumvoorraad - voorraad) DESC,
                     p.productnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def list_all_minimums(self):
        """Return every product and its physical stock for editing thresholds."""
        query = """SELECT p.product_id, p.artikelnummer, p.productnaam,
                          p.minimumvoorraad,
                          COALESCE(SUM(m.aantal), 0) AS voorraad
                   FROM Product AS p
                   LEFT JOIN Magazijnlocatie AS m ON m.product_id = p.product_id
                   GROUP BY p.product_id, p.artikelnummer, p.productnaam,
                            p.minimumvoorraad
                   ORDER BY p.productnaam, p.product_id"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()

    def set_minimum(self, product_id, minimum):
        """Atomically change a threshold after confirming the product exists."""
        from domain.errors import NotFoundError
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT product_id FROM Product WHERE product_id = %s FOR UPDATE",
                    (product_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Product niet gevonden.")
                cursor.execute(
                    "UPDATE Product SET minimumvoorraad = %s WHERE product_id = %s",
                    (minimum, product_id),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
