"""Read the case-required order status and order lines without changing data."""


class OrderStatusNotificationRepository:
    def __init__(self, connection):
        self.connection = connection

    def search_orders(self, order_id, customer_name):
        """Search by order number or partial customer name using bound SQL parameters."""
        query = """
            SELECT b.bestelling_id, k.bedrijfsnaam, b.besteld_op,
                   b.gewenste_leverdatum, b.dagdeel, b.status_naam
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            WHERE b.bestelling_id = %s OR k.bedrijfsnaam LIKE %s ESCAPE '!'
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        # Escape LIKE metacharacters, so a typed '%' or '_' remains literal.
        literal_name = customer_name.replace("!", "!!").replace("%", "!%").replace("_", "!_")
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id, f"%{literal_name}%"))
            return cursor.fetchall()

    def find_order(self, order_id):
        """The recorded status and requested date/time slot, not a delivery promise."""
        query = """
            SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum,
                   b.dagdeel, b.status_naam, k.bedrijfsnaam
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id = b.klant_id
            WHERE b.bestelling_id = %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchone()

    def find_order_lines(self, order_id):
        """Return the registered shortage choice and each recorded fulfilment step.

        A reservation, a partial order and a delivery are distinct facts. None
        alone proves whether a product is currently physically out of stock.
        """
        query = """
            SELECT p.artikelnummer, p.productnaam, br.aantal,
                   br.prijs_per_eenheid, br.afnemen_bij_tekort,
                   COALESCE(vr.aantal, 0) AS gereserveerd,
                   COALESCE((
                       SELECT SUM(dr.aantal)
                       FROM Deelorderregel AS dr
                       JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id
                       WHERE d.bestelling_id = br.bestelling_id
                         AND dr.product_id = br.product_id
                         AND d.afgerond = FALSE
                   ), 0) AS in_open_deelorder,
                   COALESCE((
                       SELECT SUM(dr.aantal)
                       FROM Deelorderregel AS dr
                       JOIN Deelorder AS d ON d.deelorder_id = dr.deelorder_id
                       WHERE d.bestelling_id = br.bestelling_id
                         AND dr.product_id = br.product_id
                         AND d.afgerond = TRUE
                   ), 0) AS in_afgeronde_deelorder,
                   COALESCE((
                       SELECT SUM(lr.aantal_geleverd)
                       FROM Levering AS lv
                       JOIN Leveringregel AS lr ON lr.levering_id = lv.levering_id
                       WHERE lv.bestelling_id = br.bestelling_id
                         AND lr.product_id = br.product_id
                         AND NOT EXISTS (
                             SELECT 1 FROM Leverpoging AS lp
                             WHERE lp.levering_id = lv.levering_id
                               AND lp.resultaat = 'afgeleverd'
                               AND lp.ontvangst_getekend = TRUE
                         )
                   ), 0) AS in_open_levering,
                   COALESCE((
                       SELECT SUM(lr.aantal_geleverd)
                       FROM Levering AS lv
                       JOIN Leveringregel AS lr ON lr.levering_id = lv.levering_id
                       WHERE lv.bestelling_id = br.bestelling_id
                         AND lr.product_id = br.product_id
                         AND EXISTS (
                             SELECT 1 FROM Leverpoging AS lp
                             WHERE lp.levering_id = lv.levering_id
                               AND lp.resultaat = 'afgeleverd'
                               AND lp.ontvangst_getekend = TRUE
                         )
                   ), 0) AS aantal_afgeleverd
            FROM Bestelregel AS br
            JOIN Product AS p ON p.product_id = br.product_id
            LEFT JOIN Voorraadreservering AS vr
                   ON vr.bestelling_id = br.bestelling_id
                  AND vr.product_id = br.product_id
            WHERE br.bestelling_id = %s
            ORDER BY p.productnaam ASC, p.product_id ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (order_id,))
            return cursor.fetchall()
