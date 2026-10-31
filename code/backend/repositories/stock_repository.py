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
        Supplier presence is derived from current offers: a product without an offer
        remains a shortage, but is not shown as reorderable.
        """
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam,
                   p.minimumvoorraad,
                   COALESCE(SUM(m.aantal), 0) AS voorraad,
                   EXISTS (
                       SELECT 1 FROM LeveranciersAanbod AS a
                       WHERE a.product_id = p.product_id
                   ) AS heeft_leverancier
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
