"""Supplier offers for a medicine, using the current purchasing data."""

from domain.supplier import Supplier


class SupplierRepository:
    def __init__(self, connection):
        self.connection = connection

    def find_offers(self, product_name):
        """Find matching products and their offers, cheapest supplier first.

        Products removed from the assortment are left out.
        """
        query = """
            SELECT p.product_id, p.productnaam, l.leverancier_id, l.naam AS leverancier,
                   l.contactpersoon, l.telefoonnummer, l.internetadres, a.inkoopprijs
            FROM Product AS p
            JOIN LeveranciersAanbod AS a ON a.product_id = p.product_id
            JOIN Leverancier AS l ON l.leverancier_id = a.leverancier_id
            WHERE p.productnaam LIKE %s AND p.intern_bestelbaar = TRUE AND p.in_assortiment = TRUE
            ORDER BY p.productnaam, a.inkoopprijs ASC, l.naam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (f"%{product_name}%",))
            return cursor.fetchall()


    def remove_offer(self, product_id, supplier_id):
        """Only disconnect a manufacturer from a product, preserving order history."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM LeveranciersAanbod WHERE product_id=%s AND leverancier_id=%s",
                    (product_id, supplier_id))
                removed=cursor.rowcount
            self.connection.commit()
            return removed
        except Exception:
            self.connection.rollback()
            raise

    def remove_from_internal_reorder_list(self, product_id):
        """Preserve the catalogue and historical order relations."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE Product SET intern_bestelbaar=FALSE WHERE product_id=%s",
                    (product_id,))
                count=cursor.rowcount
            self.connection.commit()
            return count
        except Exception:
            self.connection.rollback()
            raise

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
