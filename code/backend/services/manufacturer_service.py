"""Validate manufacturer data and purchase prices before persistence."""

from decimal import Decimal, InvalidOperation
from domain.errors import DomainError, NotFoundError

class ManufacturerService:
    def __init__(self, repository):
        self.repository = repository

    def list_manufacturers(self):
        return self.repository.all()

    def manufacturer(self, supplier_id):
        result = self.repository.get(self._positive_id(supplier_id))
        if not result:
            raise NotFoundError("Leverancier niet gevonden.")
        return result

    def create(self, values):
        return self.repository.create(self._validate(values))

    def update(self, supplier_id, values):
        ident = self._positive_id(supplier_id)
        if not self.repository.update(ident, self._validate(values)):
            raise NotFoundError("Leverancier niet gevonden.")

    def list_products(self):
        return self.repository.products()

    def prices(self, supplier_id):
        return self.repository.offers(self._positive_id(supplier_id))

    def set_price(self, supplier_id, product_id, value):
        try:
            price = Decimal(str(value).strip().replace(",", "."))
        except (InvalidOperation, ValueError):
            raise DomainError("Vul een geldige inkoopprijs in.")
        if not price.is_finite() or price < 0 or price.as_tuple().exponent < -2:
            raise DomainError("De inkoopprijs moet positief zijn en maximaal twee decimalen hebben.")
        self.repository.set_price(
            self._positive_id(supplier_id), self._positive_id(product_id), price
        )

    @staticmethod
    def _positive_id(value):
        try:
            number = int(value)
        except (ValueError, TypeError):
            raise DomainError("Ongeldig nummer.")
        if number < 1:
            raise DomainError("Ongeldig nummer.")
        return number

    @staticmethod
    def _validate(values):
        lengths = {
            "naam": 100, "adres": 255, "contactpersoon": 100,
            "telefoonnummer": 25, "internetadres": 255,
        }
        data = {key: str(values.get(key) or "").strip() for key in lengths}
        if not data["naam"] or not data["adres"]:
            raise DomainError("Naam en adres zijn verplicht.")
        if any(len(value) > lengths[key] for key, value in data.items()):
            raise DomainError("Een of meer velden zijn te lang.")
        return data

    def remove_offer(self, supplier_id, product_id):
        """Remove a manufacturer-product link, not the medicine from the assortment."""
        self.repository.remove_offer(
            self._positive_id(supplier_id), self._positive_id(product_id)
        )
