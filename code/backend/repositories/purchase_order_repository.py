"""Record a manually confirmed purchasing order in the existing EER tables."""

from domain.errors import DomainError


class PurchaseOrderRepository:
    def __init__(self, connection):
        self.connection = connection

    def create(self, supplier_id, product_id, quantity):
        """Insert a purchasing order only when supplier offers this product.

        Sending the order to the manufacturer is not automated.
        """
        connection = self.connection
        with connection.cursor() as cursor:
            try:
                cursor.execute(
                    """SELECT 1 FROM LeveranciersAanbod AS a
                       JOIN Product AS p ON p.product_id = a.product_id
                       WHERE a.leverancier_id = %s AND a.product_id = %s
                         AND p.in_assortiment = TRUE""",
                    (supplier_id, product_id),
                )
                if cursor.fetchone() is None:
                    raise DomainError("Deze leverancier levert het gekozen product niet.")
                cursor.execute(
                    "INSERT INTO Inkoopbestelling (leverancier_id, besteld_op, status_naam) VALUES (%s, CURRENT_TIMESTAMP, 'besteld')",
                    (supplier_id,),
                )
                order_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Inkoopbestelregel
                       (inkoopbestelling_id, product_id, aantal)
                       VALUES (%s, %s, %s)""",
                    (order_id, product_id, quantity),
                )
                connection.commit()
                return order_id
            except Exception:
                connection.rollback()
                raise

    def list_recorded(self):
        """List only digitally recorded supplier orders and their actual saved state."""
        query = """SELECT i.inkoopbestelling_id, i.besteld_op, i.status_naam,
                          l.naam AS leverancier, p.productnaam, r.aantal
                   FROM Inkoopbestelling AS i
                   JOIN Leverancier AS l ON l.leverancier_id = i.leverancier_id
                   JOIN Inkoopbestelregel AS r ON r.inkoopbestelling_id = i.inkoopbestelling_id
                   JOIN Product AS p ON p.product_id = r.product_id
                   ORDER BY i.besteld_op DESC, i.inkoopbestelling_id DESC, p.productnaam"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return cursor.fetchall()
