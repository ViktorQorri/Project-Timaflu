"""Read-only sales information explicitly required by the current/desired Timaflu case.

Telephone orders remain telephone orders; no unapproved order is persisted here.
"""
from domain.errors import DomainError


class SalesCaseRepository:
    def __init__(self, connection):
        self.connection = connection

    def customers(self, name=""):
        if not isinstance(name, str) or len(name) > 100:
            raise DomainError("Zoek op een bedrijfsnaam van maximaal 100 tekens.")
        term = name.strip()
        sql = """
            SELECT k.klant_id, k.bedrijfsnaam, k.telefoonnummer, k.contactpersoon,
                   delivery.adres AS afleveradres, billing.adres AS factuuradres
            FROM Klant AS k
            JOIN Adres AS delivery ON delivery.adres_id=k.afleveradres_id
            JOIN Adres AS billing ON billing.adres_id=k.betaaladres_id
            WHERE (%s = '' OR k.bedrijfsnaam LIKE %s)
            ORDER BY k.bedrijfsnaam ASC, k.klant_id ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (term, f"%{term}%"))
            return cursor.fetchall()

    def order_statuses(self, customer_id=None):
        sql = """
            SELECT b.bestelling_id, b.besteld_op, b.gewenste_leverdatum,
                   b.dagdeel, b.spoed, b.status_naam,
                   k.klant_id, k.bedrijfsnaam, address.adres AS afleveradres
            FROM Bestelling AS b
            JOIN Klant AS k ON k.klant_id=b.klant_id
            JOIN Adres AS address ON address.adres_id=b.afleveradres_id
            WHERE (%s IS NULL OR b.klant_id = %s)
            ORDER BY b.besteld_op DESC, b.bestelling_id DESC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (customer_id, customer_id))
            return cursor.fetchall()
