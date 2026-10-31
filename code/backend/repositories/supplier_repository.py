"""Supplier offers for a medicine, using the current purchasing data."""

from domain.supplier import Supplier


class SupplierRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_offers(self, product_name=None, product_id=None):
        """Compare offers for one medicine by its stable id, or exact name.

        Never use LIKE here: partial names can mix different medicines.
        The UI uses product_id when navigating from a stock shortage.
        """
        if product_id is not None:
            condition, params = "p.product_id = %s", (product_id,)
        else:
            condition, params = "p.productnaam = %s", (product_name,)
        query = """
            SELECT p.product_id, p.productnaam, l.leverancier_id, l.naam AS leverancier,
                   l.contactpersoon, l.telefoonnummer, a.inkoopprijs
            FROM Product AS p
            JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id
            JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id
            WHERE """ + condition + """ AND p.in_assortiment = TRUE
            ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, params)
            return cursor.fetchall()

    def list_all(self):
        """
        Returns:
            Every Supplier, sorted by name.
        """
        query = """
            SELECT leverancier_id, naam, contactpersoon, telefoonnummer, internetadres
            FROM Leverancier
            ORDER BY naam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query)
            return [self._to_supplier(row) for row in cursor.fetchall()]

    def get_by_id(self, supplier_id):
        """
        Args:
            supplier_id: The leverancier_id.

        Returns:
            The Supplier, or None when it does not exist.
        """
        query = """
            SELECT leverancier_id, naam, contactpersoon, telefoonnummer, internetadres
            FROM Leverancier
            WHERE leverancier_id = %s
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (supplier_id,))
            rows = cursor.fetchall()
        return self._to_supplier(rows[0]) if rows else None

    @staticmethod
    def _to_supplier(row):
        return Supplier(
            supplier_id=row["leverancier_id"],
            name=row["naam"],
            contact_person=row["contactpersoon"],
            phone_number=row["telefoonnummer"],
            website=row["internetadres"],
        )
