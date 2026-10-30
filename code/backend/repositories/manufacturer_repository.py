"""MySQL reads and transactional writes for Timaflu manufacturers."""

class ManufacturerRepository:
    def __init__(self, connection):
        self.connection = connection

    def all(self):
        sql = """SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon,
                        l.telefoonnummer, l.internetadres
                 FROM Leverancier AS l
                 JOIN Adres AS a ON a.adres_id = l.adres_id
                 ORDER BY l.naam, l.leverancier_id"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def get(self, supplier_id):
        sql = """SELECT l.leverancier_id, l.naam, a.adres, l.contactpersoon,
                        l.telefoonnummer, l.internetadres
                 FROM Leverancier AS l
                 JOIN Adres AS a ON a.adres_id = l.adres_id
                 WHERE l.leverancier_id = %s"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (supplier_id,))
            return cursor.fetchone()

    def create(self, data):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("INSERT INTO Adres (adres) VALUES (%s)", (data["adres"],))
                address_id = cursor.lastrowid
                cursor.execute(
                    """INSERT INTO Leverancier
                       (naam, adres_id, contactpersoon, telefoonnummer, internetadres)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (data["naam"], address_id, data["contactpersoon"],
                     data["telefoonnummer"], data["internetadres"]),
                )
                supplier_id = cursor.lastrowid
            self.connection.commit()
            return supplier_id
        except Exception:
            self.connection.rollback()
            raise

    def update(self, supplier_id, data):
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT adres_id FROM Leverancier WHERE leverancier_id = %s FOR UPDATE",
                    (supplier_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    self.connection.rollback()
                    return False
                # Preserve shared addresses rather than editing them in place.
                cursor.execute("INSERT INTO Adres (adres) VALUES (%s)", (data["adres"],))
                address_id = cursor.lastrowid
                cursor.execute(
                    """UPDATE Leverancier
                       SET naam = %s, adres_id = %s, contactpersoon = %s,
                           telefoonnummer = %s, internetadres = %s
                       WHERE leverancier_id = %s""",
                    (data["naam"], address_id, data["contactpersoon"],
                     data["telefoonnummer"], data["internetadres"], supplier_id),
                )
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise

    def products(self):
        sql = """SELECT product_id, productnaam, artikelnummer
                 FROM Product ORDER BY productnaam, product_id"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def offers(self, supplier_id):
        sql = """SELECT a.product_id, p.productnaam, a.inkoopprijs
                 FROM LeveranciersAanbod AS a
                 JOIN Product AS p ON p.product_id = a.product_id
                 WHERE a.leverancier_id = %s
                 ORDER BY p.productnaam, a.product_id"""
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(sql, (supplier_id,))
            return cursor.fetchall()

    def set_price(self, supplier_id, product_id, price):
        from domain.errors import NotFoundError
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM Leverancier WHERE leverancier_id = %s",
                    (supplier_id,),
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Leverancier niet gevonden.")
                cursor.execute(
                    "SELECT 1 FROM Product WHERE product_id = %s", (product_id,)
                )
                if cursor.fetchone() is None:
                    raise NotFoundError("Product niet gevonden.")
                cursor.execute(
                    """INSERT INTO LeveranciersAanbod
                       (leverancier_id, product_id, inkoopprijs)
                       VALUES (%s, %s, %s)
                       ON DUPLICATE KEY UPDATE inkoopprijs = VALUES(inkoopprijs)""",
                    (supplier_id, product_id, price),
                )
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise
