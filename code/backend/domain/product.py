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
    supplier_offers: list["SupplierOffer"] = field(default_factory=list)

    def checkStock(self, physical_stock, reserved_stock=0, requested_quantity=1):
        """Check physical inventory less recorded reservations (AD04)."""
        return max(0, int(physical_stock) - int(reserved_stock)) >= int(requested_quantity)

    def checkMinimumStock(self, physical_stock):
        """Flag a medicine below its configured physical minimum (AD03)."""
        return int(physical_stock) < self.minimum_stock

    def findSuppliersByPrice(self):
        """Rank linked supplier offers by price; no supplier is contacted automatically."""
        return sorted(self.supplier_offers, key=lambda offer: (offer.purchase_price, offer.supplier_id))

    def removeSupplier(self, supplier_id):
        """Modify this in-memory offer collection; persistence belongs to the repository."""
        before = len(self.supplier_offers)
        self.supplier_offers = [offer for offer in self.supplier_offers if offer.supplier_id != supplier_id]
        return before - len(self.supplier_offers)

    def removeFromAssortment(self):
        """Mark this domain instance inactive without erasing historical database rows."""
        self.in_assortment = False


@dataclass
class SupplierOffer:
    """The purchase price for which a supplier delivers a product."""

    supplier_id: int
    purchase_price: Decimal
