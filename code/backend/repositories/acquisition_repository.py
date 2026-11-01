"""Database access for prospective customers and acquisition follow-ups."""

from domain.errors import ConflictError, NotFoundError


FOLLOW_UPS_QUERY = """
    SELECT p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
           p.contactgegevens, a.adres, MAX(v.bezoekdatum) AS laatste_bezoek
    FROM PotentieleKlant AS p
    JOIN Adres AS a ON a.adres_id = p.adres_id
    JOIN Acquisitiebezoek AS v ON v.potentiele_klant_id = p.potentiele_klant_id
    WHERE p.opvolging_afgesloten = FALSE
      AND NOT EXISTS (
          SELECT 1 FROM Bestelling AS b WHERE b.klant_id = p.klant_id
      )
    GROUP BY p.potentiele_klant_id, p.bedrijfsnaam, p.contactpersoon,
             p.contactgegevens, a.adres
    HAVING MAX(v.bezoekdatum) <= DATE_SUB(CURDATE(), INTERVAL 1 MONTH)
    ORDER BY laatste_bezoek ASC, p.bedrijfsnaam ASC
"""


class AcquisitionRepository:
    def __init__(self, connection):
        """Create a repository that uses the request's database connection.

        Args:
            connection: An open MySQL connection.
        """
        self.connection = connection

    def find_due_follow_ups(self):
        """Return open prospects whose last visit was at least one month ago.

        Returns:
            A list of prospect rows with contact details and the latest visit date.
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(FOLLOW_UPS_QUERY)
            return cursor.fetchall()

    def register_prospect(self, prospect):
        """Save a prospect, its address and its acquisition visit atomically.

        Args:
            prospect: Validated prospect details, including the visit date.

        Returns:
            The new prospective-customer identifier.
        """
        connection = self.connection
        try:
            with connection.cursor() as cursor:
                address_id = self._insert_address(cursor, prospect["address"])
                cursor.execute(
                    """INSERT INTO PotentieleKlant
                           (bedrijfsnaam, contactpersoon, contactgegevens, adres_id)
                       VALUES (%s, %s, %s, %s)""",
                    (
                        prospect["company_name"],
                        prospect["contact_person"],
                        prospect["contact_details"],
                        address_id,
                    ),
                )
                prospect_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Acquisitiebezoek (potentiele_klant_id, bezoekdatum)
                       VALUES (%s, %s)""",
                    (prospect_id, prospect["visit_date"]),
                )
            connection.commit()
            return prospect_id
        except Exception:
            connection.rollback()
            raise

    def complete_follow_up(self, prospect_id, outcome, customer=None):
        """Record a due follow-up outcome and optionally convert its prospect.

        Args:
            prospect_id: The prospect being followed up.
            outcome: ``no_interest``, ``no_consent`` or ``convert``.
            customer: Validated customer addresses and optional phone on conversion.

        Returns:
            The created customer identifier, or None when no account was created.
        """
        connection = self.connection
        customer_id = None
        try:
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(
                    """SELECT klant_id, opvolging_afgesloten, bedrijfsnaam, contactpersoon
                       FROM PotentieleKlant
                       WHERE potentiele_klant_id = %s
                       FOR UPDATE""",
                    (prospect_id,),
                )
                prospect = cursor.fetchone()
                if prospect is None:
                    raise NotFoundError("Potentiële klant niet gevonden.")
                if prospect["opvolging_afgesloten"]:
                    raise ConflictError("Deze acquisitieopvolging is al afgesloten.")

                cursor.execute(
                    """SELECT MAX(bezoekdatum) <= DATE_SUB(CURDATE(), INTERVAL 1 MONTH) AS is_due
                       FROM Acquisitiebezoek
                       WHERE potentiele_klant_id = %s""",
                    (prospect_id,),
                )
                due = cursor.fetchone()
                if due is None or not due["is_due"]:
                    raise ConflictError("Deze potentiële klant is nog niet aan opvolging toe.")

                cursor.execute(
                    "SELECT bestelling_id FROM Bestelling WHERE klant_id = %s LIMIT 1",
                    (prospect["klant_id"],),
                )
                if cursor.fetchone() is not None:
                    raise ConflictError("Deze potentiële klant heeft al een bestelling geplaatst.")

                if outcome in ("no_interest", "no_consent"):
                    cursor.execute(
                        """UPDATE PotentieleKlant SET opvolging_afgesloten = TRUE
                           WHERE potentiele_klant_id = %s""",
                        (prospect_id,),
                    )
                else:
                    delivery_address_id = self._insert_address(
                        cursor, customer["delivery_address"]
                    )
                    invoice_address_id = self._insert_address(
                        cursor, customer["invoice_address"]
                    )
                    cursor.execute(
                        """INSERT INTO Klant
                               (bedrijfsnaam, telefoonnummer, contactpersoon,
                                afleveradres_id, betaaladres_id, eenmalige_korting_toegezegd)
                           VALUES (%s, %s, %s, %s, %s, TRUE)""",
                        (
                            prospect["bedrijfsnaam"],
                            customer["phone_number"],
                            prospect["contactpersoon"],
                            delivery_address_id,
                            invoice_address_id,
                        ),
                    )
                    customer_id = cursor.lastrowid
                    cursor.execute(
                        """UPDATE PotentieleKlant
                           SET klant_id = %s, opvolging_afgesloten = TRUE
                           WHERE potentiele_klant_id = %s""",
                        (customer_id, prospect_id),
                    )
            connection.commit()
            return customer_id
        except Exception:
            connection.rollback()
            raise

    @staticmethod
    def _insert_address(cursor, address):
        """Insert an address and return its generated identifier."""
        cursor.execute("INSERT INTO Adres (adres) VALUES (%s)", (address,))
        return cursor.lastrowid
