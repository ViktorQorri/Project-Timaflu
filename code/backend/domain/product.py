from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class ProductActiveIngredient:
    """An active ingredient of a product and its amount, for example paracetamol 500 mg."""

    ingredient_name: str
    quantity: str


@dataclass
class Product:
    """A medicine in the Timaflu catalog. Names follow the class diagram, columns the EER.

    product_id is None for a product that is not saved yet. A product that is removed from
    the assortment stays in the database, because orders, deliveries and invoices refer to it.
    """

    product_id: int | None
    article_number: str
    order_code: str
    product_name: str
    price_per_bulk_package: Decimal
    package_type: str | None
    number_of_retail_packages: int
    short_description: str | None
    long_description: str | None
    minimum_order_quantity: int
    minimum_stock: int
    active_ingredients: list[ProductActiveIngredient] = field(default_factory=list)
    in_assortment: bool = True


@dataclass
class SupplierOffer:
    """The purchase price for which a supplier delivers a product."""

    supplier_id: int
    purchase_price: Decimal
