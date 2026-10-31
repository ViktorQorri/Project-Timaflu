"""Sales reports based on issued invoices and their saved snapshots."""


class SalesReportRepository:
    def __init__(self, connection):
        self.connection = connection

    def revenue_per_customer(self, start, end):
        """Return invoice totals and unknown-snapshot counts per customer."""
        query = """
            SELECT k.klant_id, k.bedrijfsnaam,
                   COUNT(f.factuur_id) AS aantal_facturen,
                   COUNT(f.totaal_bedrag) AS bekende_facturen,
                   COUNT(f.factuur_id) - COUNT(f.totaal_bedrag) AS onbekende_facturen,
                   SUM(f.totaal_bedrag) AS bekend_factuurbedrag
            FROM Factuur AS f
            JOIN Klant AS k ON k.klant_id = f.klant_id
            WHERE f.factuurdatum >= %s AND f.factuurdatum < %s
            GROUP BY k.klant_id, k.bedrijfsnaam
            ORDER BY bekend_factuurbedrag DESC, k.bedrijfsnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (start, end))
            return cursor.fetchall()

    def revenue_per_period(self, date_format, start, end):
        """Return invoice totals and unknown-snapshot counts by invoice period."""
        query = """
            SELECT DATE_FORMAT(f.factuurdatum, %s) AS periode,
                   COUNT(f.factuur_id) AS aantal_facturen,
                   COUNT(f.totaal_bedrag) AS bekende_facturen,
                   COUNT(f.factuur_id) - COUNT(f.totaal_bedrag) AS onbekende_facturen,
                   SUM(f.totaal_bedrag) AS bekend_factuurbedrag
            FROM Factuur AS f
            WHERE f.factuurdatum >= %s AND f.factuurdatum < %s
            GROUP BY periode
            ORDER BY periode ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (date_format, start, end))
            return cursor.fetchall()

    def best_selling_products(self, start, end, limit):
        """Rank invoiced medicines by the quantity actually delivered."""
        query = """
            SELECT p.product_id, p.artikelnummer, p.productnaam,
                   SUM(lr.aantal_geleverd) AS aantal_verkocht
            FROM Factuur AS f
            JOIN Leveringregel AS lr ON lr.factuur_id = f.factuur_id
            JOIN Product AS p ON p.product_id = lr.product_id
            WHERE f.factuurdatum >= %s AND f.factuurdatum < %s
            GROUP BY p.product_id, p.artikelnummer, p.productnaam
            ORDER BY aantal_verkocht DESC, p.productnaam ASC
            LIMIT %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (start, end, limit))
            return cursor.fetchall()
