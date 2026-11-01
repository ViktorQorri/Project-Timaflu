"""Central customer data for sales (AD07 Manage customer data), stored in Klant and Adres."""

from domain.errors import NotFoundError


class CustomerRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_customers(self, search, year):
        """Return matching customers with both addresses, annual revenue and discount for a year.

        Annual revenue is the sum of persisted net totals from paid invoices in that year.
        It is unknown when any such invoice has no recorded snapshot.
        """
        query = """
            SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                   af.adres AS afleveradres, ba.adres AS factuuradres,
                   CASE
                       WHEN o.paid_count IS NULL THEN 0
                       WHEN o.paid_count = o.known_amount_count THEN o.jaaromzet
                       ELSE NULL
                   END AS jaaromzet,
                   kk.percentage AS kortingspercentage
            FROM Klant AS k
            JOIN Adres AS af ON af.adres_id = k.afleveradres_id
            JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
            LEFT JOIN (
                SELECT f.klant_id,
                       COUNT(*) AS paid_count,
                       COUNT(f.totaal_bedrag) AS known_amount_count,
                       SUM(f.totaal_bedrag) AS jaaromzet
                FROM FactuurOverzicht AS f
                WHERE YEAR(f.betaald_op) = %s
                GROUP BY f.klant_id
            ) AS o ON o.klant_id = k.klant_id
            LEFT JOIN Klantkorting AS kk ON kk.klant_id = k.klant_id
                                        AND kk.kalenderjaar = %s
            WHERE k.actief = TRUE
              AND (k.bedrijfsnaam LIKE %s OR k.contactpersoon LIKE %s
               OR k.telefoonnummer LIKE %s)
            ORDER BY k.bedrijfsnaam ASC, k.klant_id ASC
        """
        pattern = f"%{search}%"
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (year, year + 1, pattern, pattern, pattern))
            return cursor.fetchall()

    def find_customer(self, customer_id):
        """Return one customer with both addresses, or None when it does not exist."""
        query = """
            SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                   af.adres AS afleveradres, ba.adres AS factuuradres
            FROM Klant AS k
            JOIN Adres AS af ON af.adres_id = k.afleveradres_id
            JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
            WHERE k.klant_id = %s AND k.actief = TRUE
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (customer_id,))
            return cursor.fetchone()

    def create(self, customer):
        """Insert both addresses and the customer in one transaction.

        Returns:
            The new klant_id.
        """
        connection = self.connection
        try:
            with connection.cursor(dictionary=True) as cursor:
                delivery_id = self._insert_address(cursor, customer["afleveradres"])
                invoice_id = self._insert_address(cursor, customer["factuuradres"])
                cursor.execute(
                    """INSERT INTO Klant (bedrijfsnaam, telefoonnummer, contactpersoon,
                                          afleveradres_id, betaaladres_id, eenmalige_korting_toegezegd)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (customer["bedrijfsnaam"], customer["telefoonnummer"],
                     customer["contactpersoon"], delivery_id, invoice_id,
                     customer.get("eenmalige_korting_toegezegd", False)),
                )
                customer_id = cursor.lastrowid
            connection.commit()
            return customer_id
        except Exception:
            connection.rollback()
            raise

    def update(self, customer_id, customer):
        """Save changed customer data in one transaction.

        A changed address gets a new Adres row instead of overwriting the old one,
        so orders that point to the old address keep the address they were placed with.
        """
        connection = self.connection
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT k.afleveradres_id, af.adres AS afleveradres,
                              k.betaaladres_id, ba.adres AS factuuradres
                       FROM Klant AS k
                       JOIN Adres AS af ON af.adres_id = k.afleveradres_id
                       JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
                       WHERE k.klant_id = %s AND k.actief = TRUE
                       FOR UPDATE""",
                    (customer_id,),
                )
                current = cursor.fetchone()
                if current is None:
                    raise NotFoundError("Deze klant bestaat niet.")
                delivery_id = current["afleveradres_id"]
                if customer["afleveradres"] != current["afleveradres"]:
                    delivery_id = self._insert_address(cursor, customer["afleveradres"])
                invoice_id = current["betaaladres_id"]
                if customer["factuuradres"] != current["factuuradres"]:
                    invoice_id = self._insert_address(cursor, customer["factuuradres"])
                cursor.execute(
                    """UPDATE Klant
                       SET bedrijfsnaam = %s, telefoonnummer = %s, contactpersoon = %s,
                           afleveradres_id = %s, betaaladres_id = %s
                       WHERE klant_id = %s""",
                    (customer["bedrijfsnaam"], customer["telefoonnummer"],
                     customer["contactpersoon"], delivery_id, invoice_id, customer_id),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    def deactivate(self, customer_id):
        """Deactivate without destroying orders, invoices, discounts or acquisition links."""
        connection = self.connection
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT klant_id FROM Klant WHERE klant_id = %s AND actief = TRUE FOR UPDATE",
                    (customer_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Deze actieve klant bestaat niet.")
                cursor.execute(
                    "UPDATE Klant SET actief = FALSE WHERE klant_id = %s",
                    (customer_id,),
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _insert_address(cursor, address):
        cursor.execute("INSERT INTO Adres (adres) VALUES (%s)", (address,))
        return cursor.lastrowid
