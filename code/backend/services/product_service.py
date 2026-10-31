"""Managing the product catalog (issue #13, AD24 Evaluate new medicine)."""

from decimal import Decimal, InvalidOperation

from domain.errors import ConflictError, DomainError, NotFoundError
from domain.product import Product, ProductActiveIngredient, SupplierOffer

# Largest value that fits in DECIMAL(10,2).
MAX_PRICE = Decimal("99999999.99")

NOT_IN_ASSORTMENT = "Dit product bestaat niet of staat niet meer in het assortiment."


class ProductService:
    """Adds, changes and removes products in the catalog."""

    def __init__(self, product_repository, supplier_repository):
        """
        Args:
            product_repository: A ProductRepository, or a fake one in tests.
            supplier_repository: A SupplierRepository, or a fake one in tests.
        """
        self.product_repository = product_repository
        self.supplier_repository = supplier_repository

    def catalog(self):
        """
        Returns:
            Every Product in the assortment, sorted by name.
        """
        return self.product_repository.list_in_assortment()

    def suppliers(self):
        """
        Returns:
            Every Supplier, to choose the first supplier of a new product.
        """
        return self.supplier_repository.list_all()

    def get_product(self, product_id):
        """
        Args:
            product_id: The product_id.

        Returns:
            The Product in the assortment.

        Raises:
            NotFoundError: The product does not exist or is removed from the assortment.
        """
        product = self.product_repository.get_by_id(product_id)
        if product is None:
            raise NotFoundError(NOT_IN_ASSORTMENT)
        return product

    def add_product(self, data):
        """Validate a new medicine with its supplier offer and add it to the assortment.

        Args:
            data: The entered values as strings, see read_product() and read_supplier_offer().

        Returns:
            The new product_id.

        Raises:
            DomainError: A value is missing or invalid, or the supplier does not exist.
            ConflictError: The article number or order code is already in use.
        """
        # De casus vereist een expliciet directiebesluit vóór opname in het assortiment.
        if data.get("director_approved") != "yes":
            raise DomainError("Bevestig eerst dat de directie dit medicijn heeft goedgekeurd.")
        product = read_product(data)
        offer = read_supplier_offer(data)
        if self.supplier_repository.get_by_id(offer.supplier_id) is None:
            raise DomainError("Kies een bestaande leverancier.")
        self._check_codes_are_free(product)
        return self.product_repository.add(product, offer)

    def update_product(self, product_id, data):
        """Validate and save the changed data of a product in the assortment.

        Args:
            product_id: The product_id.
            data: The entered values as strings, see read_product().

        Raises:
            DomainError: A value is missing or invalid.
            ConflictError: The article number or order code is used by another product.
            NotFoundError: The product does not exist or is removed from the assortment.
        """
        product = read_product(data, product_id)
        self._check_codes_are_free(product)
        if not self.product_repository.update(product):
            raise NotFoundError(NOT_IN_ASSORTMENT)

    def remove_from_assortment(self, product_id):
        """Take a product out of the assortment. Its history stays in the database.

        Args:
            product_id: The product_id.

        Returns:
            The removed Product, to name it in the confirmation.

        Raises:
            NotFoundError: The product does not exist or is already removed.
        """
        product = self.get_product(product_id)
        if not self.product_repository.remove_from_assortment(product_id):
            raise NotFoundError(NOT_IN_ASSORTMENT)
        return product

    def _check_codes_are_free(self, product):
        owners = self.product_repository.find_code_owners(
            product.article_number, product.order_code, product.product_id
        )
        for owner in owners:
            removed = "" if owner["in_assortiment"] else " (verwijderd uit het assortiment)"
            if owner["artikelnummer"] == product.article_number:
                raise ConflictError(
                    f"Artikelnummer {product.article_number} is al in gebruik bij"
                    f" {owner['productnaam']}{removed}."
                )
            raise ConflictError(
                f"Bestelcode {product.order_code} is al in gebruik bij"
                f" {owner['productnaam']}{removed}."
            )


def read_product(data, product_id=None):
    """Turn the entered values into a Product, checking the rules from the EER.

    Args:
        data: A dict with article_number, order_code, product_name, price_per_bulk_package,
            package_type, number_of_retail_packages, short_description, long_description,
            minimum_order_quantity, minimum_stock, and the lists ingredient_name and
            ingredient_quantity. Empty ingredient rows are skipped.
        product_id: The product_id of an existing product, or None for a new one.

    Returns:
        The Product.

    Raises:
        DomainError: A value is missing or invalid.
    """
    return Product(
        product_id=product_id,
        article_number=_text(data, "article_number", "Artikelnummer", 50),
        order_code=_text(data, "order_code", "Bestelcode", 50),
        product_name=_text(data, "product_name", "Naam van het medicijn", 100),
        price_per_bulk_package=_price(data, "price_per_bulk_package", "Prijs per grootverpakking"),
        package_type=_text(data, "package_type", "Verpakkingssoort", 50, required=False),
        number_of_retail_packages=_whole_number(
            data, "number_of_retail_packages", "Detailverpakkingen per grootverpakking", minimum=1
        ),
        short_description=_text(
            data, "short_description", "Korte omschrijving", 255, required=False
        ),
        long_description=_text(
            data, "long_description", "Lange omschrijving", 65535, required=False
        ),
        minimum_order_quantity=_whole_number(
            data, "minimum_order_quantity", "Minimale bestelhoeveelheid", minimum=1
        ),
        minimum_stock=_whole_number(data, "minimum_stock", "Minimumvoorraad", minimum=0),
        active_ingredients=_ingredients(data),
    )


def read_supplier_offer(data):
    """Turn the chosen supplier and purchase price into a SupplierOffer.

    Args:
        data: A dict with supplier_id and purchase_price.

    Returns:
        The SupplierOffer.

    Raises:
        DomainError: The supplier is not chosen or the price is invalid.
    """
    try:
        supplier_id = int(str(data.get("supplier_id") or "").strip())
    except ValueError:
        raise DomainError("Kies een leverancier.")
    return SupplierOffer(
        supplier_id=supplier_id,
        purchase_price=_price(data, "purchase_price", "Inkoopprijs"),
    )


def _text(data, key, label, max_length, required=True):
    value = str(data.get(key) or "").strip()
    if not value:
        if required:
            raise DomainError(f"{label} is verplicht.")
        return None
    if len(value) > max_length:
        raise DomainError(f"{label} mag maximaal {max_length} tekens zijn.")
    return value


def _whole_number(data, key, label, minimum):
    value = str(data.get(key) or "").strip()
    try:
        number = int(value)
    except ValueError:
        raise DomainError(f"{label} moet een heel getal zijn.")
    if number < minimum:
        raise DomainError(f"{label} moet minimaal {minimum} zijn.")
    return number


def _price(data, key, label):
    # Accept both 12.50 and the Dutch 12,50.
    value = str(data.get(key) or "").strip().replace(",", ".")
    try:
        price = Decimal(value)
    except InvalidOperation:
        raise DomainError(f"{label} moet een bedrag zijn, bijvoorbeeld 12,50.")
    if not price.is_finite() or price < 0:
        raise DomainError(f"{label} moet 0 of meer zijn.")
    if price > MAX_PRICE or price != price.quantize(Decimal("0.01")):
        raise DomainError(f"{label} mag maximaal {MAX_PRICE} zijn, met hooguit 2 decimalen.")
    return price.quantize(Decimal("0.01"))


def _ingredients(data):
    names = data.get("ingredient_name") or []
    quantities = data.get("ingredient_quantity") or []
    ingredients = []
    seen = set()
    for index in range(max(len(names), len(quantities))):
        name = (names[index] if index < len(names) else "").strip()
        quantity = (quantities[index] if index < len(quantities) else "").strip()
        if not name and not quantity:
            continue
        if not name or not quantity:
            raise DomainError("Vul bij elke werkzame stof zowel de naam als de hoeveelheid in.")
        if len(name) > 100 or len(quantity) > 50:
            raise DomainError(
                "De naam van een werkzame stof mag maximaal 100 tekens zijn, de hoeveelheid 50."
            )
        if name.casefold() in seen:
            raise DomainError(f"Werkzame stof {name} is twee keer ingevuld.")
        seen.add(name.casefold())
        ingredients.append(ProductActiveIngredient(ingredient_name=name, quantity=quantity))
    if not ingredients:
        raise DomainError("Vul minimaal één werkzame stof in.")
    return ingredients
