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
                    "INSERT INTO Inkoopbestelling (leverancier_id) VALUES (%s)",
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
