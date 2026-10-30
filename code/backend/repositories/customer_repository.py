"""Central customer data for sales (AD07 Manage customer data), stored in Klant and Adres."""

from domain.errors import ConflictError, NotFoundError


class CustomerRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_customers(self, search, year):
        """Return matching customers with both addresses, annual revenue and discount for a year.

        Annual revenue is not stored: the case adds paid invoice amounts to it, so it is the
        sum of delivered lines on invoices paid in that year (gross, as invoice totals are not stored).
        """
        query = """
            SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                   af.adres AS afleveradres, ba.adres AS factuuradres,
                   COALESCE(o.jaaromzet, 0) AS jaaromzet,
                   kk.percentage AS kortingspercentage
            FROM Klant AS k
            JOIN Adres AS af ON af.adres_id = k.afleveradres_id
            JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
            LEFT JOIN (
                SELECT f.klant_id,
                       SUM(lr.aantal_geleverd * br.prijs_per_eenheid) AS jaaromzet
                FROM Factuur AS f
                JOIN Leveringregel AS lr ON lr.factuur_id = f.factuur_id
                JOIN Levering AS l ON l.levering_id = lr.levering_id
                JOIN Bestelregel AS br ON br.bestelling_id = l.bestelling_id
                                      AND br.product_id = lr.product_id
                WHERE YEAR(f.betaald_op) = %s
                GROUP BY f.klant_id
            ) AS o ON o.klant_id = k.klant_id
            LEFT JOIN Klantkorting AS kk ON kk.klant_id = k.klant_id
                                        AND kk.kalenderjaar = %s
            WHERE k.bedrijfsnaam LIKE %s OR k.contactpersoon LIKE %s
               OR k.telefoonnummer LIKE %s
            ORDER BY k.bedrijfsnaam ASC, k.klant_id ASC
        """
        pattern = f"%{search}%"
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (year, year, pattern, pattern, pattern))
            return cursor.fetchall()

    def find_customer(self, customer_id):
        """Return one customer with both addresses, or None when it does not exist."""
        query = """
            SELECT k.klant_id, k.bedrijfsnaam, k.contactpersoon, k.telefoonnummer,
                   af.adres AS afleveradres, ba.adres AS factuuradres
            FROM Klant AS k
            JOIN Adres AS af ON af.adres_id = k.afleveradres_id
            JOIN Adres AS ba ON ba.adres_id = k.betaaladres_id
            WHERE k.klant_id = %s
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
                                          afleveradres_id, betaaladres_id)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (customer["bedrijfsnaam"], customer["telefoonnummer"],
                     customer["contactpersoon"], delivery_id, invoice_id),
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
                       WHERE k.klant_id = %s
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

    def delete(self, customer_id):
        """Delete a customer without order, invoice or acquisition history.

        Its yearly discounts go with it. Addresses stay, as Adres rows can be shared.
        """
        connection = self.connection
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    "SELECT klant_id FROM Klant WHERE klant_id = %s FOR UPDATE",
                    (customer_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Deze klant bestaat niet.")
                cursor.execute(
                    """SELECT (SELECT COUNT(*) FROM Bestelling WHERE klant_id = %s) AS bestellingen,
                              (SELECT COUNT(*) FROM Factuur WHERE klant_id = %s) AS facturen,
                              (SELECT COUNT(*) FROM PotentieleKlant WHERE klant_id = %s) AS acquisities""",
                    (customer_id, customer_id, customer_id),
                )
                history = cursor.fetchone()
                if any(history.values()):
                    raise ConflictError(
                        "Deze klant heeft bestellingen, facturen of een acquisitiedossier "
                        "en kan daarom niet worden verwijderd."
                    )
                cursor.execute("DELETE FROM Klantkorting WHERE klant_id = %s", (customer_id,))
                cursor.execute("DELETE FROM Klant WHERE klant_id = %s", (customer_id,))
            connection.commit()
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _insert_address(cursor, address):
        cursor.execute("INSERT INTO Adres (adres) VALUES (%s)", (address,))
        return cursor.lastrowid
