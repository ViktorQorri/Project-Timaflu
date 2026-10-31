"""The product catalog: products, their active ingredients and the first supplier offer."""

from domain.product import Product, ProductActiveIngredient

PRODUCT_COLUMNS = """
    p.product_id, p.artikelnummer, p.bestelcode, p.productnaam,
    p.prijs_per_grootverpakking, p.verpakkingssoort, p.aantal_detailverpakkingen,
    p.korte_omschrijving, p.lange_omschrijving, p.minimale_bestelhoeveelheid,
    p.minimumvoorraad, p.in_assortiment
"""


class ProductRepository:
    """All database access for the Product aggregate (Product and ProductWerkzameStof)."""

    def __init__(self, connection):
        """
        Args:
            connection: An open mysql.connector connection.
        """
        self.connection = connection

    def list_in_assortment(self):
        """
        Returns:
            Every Product in the assortment with its active ingredients, sorted by name.
        """
        products_query = f"""
            SELECT {PRODUCT_COLUMNS}
            FROM Product AS p
            WHERE p.in_assortiment = TRUE
            ORDER BY p.productnaam ASC, p.artikelnummer ASC
        """
        ingredients_query = """
            SELECT w.product_id, w.stofnaam, w.hoeveelheid
            FROM ProductWerkzameStof AS w
            JOIN Product AS p ON p.product_id = w.product_id
            WHERE p.in_assortiment = TRUE
            ORDER BY w.stofnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(products_query)
            products = [self._to_product(row) for row in cursor.fetchall()]
            cursor.execute(ingredients_query)
            ingredient_rows = cursor.fetchall()

        by_id = {product.product_id: product for product in products}
        for row in ingredient_rows:
            by_id[row["product_id"]].active_ingredients.append(self._to_ingredient(row))
        return products

    def get_by_id(self, product_id):
        """
        Args:
            product_id: The product_id.

        Returns:
            The Product in the assortment with its active ingredients, or None when it does
            not exist or is removed from the assortment.
        """
        product_query = f"""
            SELECT {PRODUCT_COLUMNS}
            FROM Product AS p
            WHERE p.product_id = %s AND p.in_assortiment = TRUE
        """
        ingredients_query = """
            SELECT product_id, stofnaam, hoeveelheid
            FROM ProductWerkzameStof
            WHERE product_id = %s
            ORDER BY stofnaam ASC
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(product_query, (product_id,))
            rows = cursor.fetchall()
            if not rows:
                return None
            product = self._to_product(rows[0])
            cursor.execute(ingredients_query, (product_id,))
            product.active_ingredients = [self._to_ingredient(r) for r in cursor.fetchall()]
        return product

    def find_code_owners(self, article_number, order_code, exclude_product_id=None):
        """Find products that already use an article number or order code.

        Removed products are included, because the columns are unique for every row.

        Args:
            article_number: The artikelnummer to look for.
            order_code: The bestelcode to look for.
            exclude_product_id: A product to skip, the one being edited. None skips nothing.

        Returns:
            A list of dicts with product_id, artikelnummer, bestelcode, productnaam
            and in_assortiment.
        """
        query = """
            SELECT product_id, artikelnummer, bestelcode, productnaam, in_assortiment
            FROM Product
            WHERE (artikelnummer = %s OR bestelcode = %s)
              AND (%s IS NULL OR product_id <> %s)
        """
        with self.connection.cursor(dictionary=True) as cursor:
            cursor.execute(
                query, (article_number, order_code, exclude_product_id, exclude_product_id)
            )
            return cursor.fetchall()

    def add(self, product, supplier_offer):
        """Save a new product, its active ingredients and its first supplier offer.

        Everything is saved in one transaction, so a failure leaves no half product behind.

        Args:
            product: The Product to save. Its product_id is ignored.
            supplier_offer: The SupplierOffer for this product.

        Returns:
            The new product_id.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO Product (
                        artikelnummer, bestelcode, productnaam, prijs_per_grootverpakking,
                        verpakkingssoort, aantal_detailverpakkingen, korte_omschrijving,
                        lange_omschrijving, minimale_bestelhoeveelheid, minimumvoorraad
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    self._product_values(product),
                )
                product_id = cursor.lastrowid
                self._insert_ingredients(cursor, product_id, product.active_ingredients)
                cursor.execute(
                    """
                    INSERT INTO LeveranciersAanbod (leverancier_id, product_id, inkoopprijs)
                    VALUES (%s, %s, %s)
                    """,
                    (supplier_offer.supplier_id, product_id, supplier_offer.purchase_price),
                )
            self.connection.commit()
            return product_id
        except Exception:
            self.connection.rollback()
            raise

    def update(self, product):
        """Save the changed data and active ingredients of a product in the assortment.

        The active ingredients are replaced as a whole, in the same transaction.

        Args:
            product: The Product with its product_id.

        Returns:
            True when the product was found in the assortment and saved, otherwise False.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT product_id FROM Product"
                    " WHERE product_id = %s AND in_assortiment = TRUE FOR UPDATE",
                    (product.product_id,),
                )
                if not cursor.fetchall():
                    self.connection.rollback()
                    return False
                cursor.execute(
                    """
                    UPDATE Product
                    SET artikelnummer = %s, bestelcode = %s, productnaam = %s,
                        prijs_per_grootverpakking = %s, verpakkingssoort = %s,
                        aantal_detailverpakkingen = %s, korte_omschrijving = %s,
                        lange_omschrijving = %s, minimale_bestelhoeveelheid = %s,
                        minimumvoorraad = %s
                    WHERE product_id = %s
                    """,
                    (*self._product_values(product), product.product_id),
                )
                cursor.execute(
                    "DELETE FROM ProductWerkzameStof WHERE product_id = %s",
                    (product.product_id,),
                )
                self._insert_ingredients(cursor, product.product_id, product.active_ingredients)
            self.connection.commit()
            return True
        except Exception:
            self.connection.rollback()
            raise

    def remove_from_assortment(self, product_id):
        """Take a product out of the assortment without deleting it.

        The row stays, so orders, deliveries and invoices that refer to it keep working.

        Args:
            product_id: The product_id.

        Returns:
            True when the product was in the assortment and is now removed, otherwise False.
        """
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE Product SET in_assortiment = FALSE"
                    " WHERE product_id = %s AND in_assortiment = TRUE",
                    (product_id,),
                )
                removed = cursor.rowcount == 1
            self.connection.commit()
            return removed
        except Exception:
            self.connection.rollback()
            raise

    @staticmethod
    def _insert_ingredients(cursor, product_id, ingredients):
        for ingredient in ingredients:
            cursor.execute(
                """
                INSERT INTO ProductWerkzameStof (product_id, stofnaam, hoeveelheid)
                VALUES (%s, %s, %s)
                """,
                (product_id, ingredient.ingredient_name, ingredient.quantity),
            )

    @staticmethod
    def _product_values(product):
        return (
            product.article_number,
            product.order_code,
            product.product_name,
            product.price_per_bulk_package,
            product.package_type,
            product.number_of_retail_packages,
            product.short_description,
            product.long_description,
            product.minimum_order_quantity,
            product.minimum_stock,
        )

    @staticmethod
    def _to_product(row):
        return Product(
            product_id=row["product_id"],
            article_number=row["artikelnummer"],
            order_code=row["bestelcode"],
            product_name=row["productnaam"],
            price_per_bulk_package=row["prijs_per_grootverpakking"],
            package_type=row["verpakkingssoort"],
            number_of_retail_packages=row["aantal_detailverpakkingen"],
            short_description=row["korte_omschrijving"],
            long_description=row["lange_omschrijving"],
            minimum_order_quantity=row["minimale_bestelhoeveelheid"],
            minimum_stock=row["minimumvoorraad"],
            in_assortment=bool(row["in_assortiment"]),
        )

    @staticmethod
    def _to_ingredient(row):
        return ProductActiveIngredient(ingredient_name=row["stofnaam"], quantity=row["hoeveelheid"])
