"""Compose shortage and supplier lookup without automating supplier contact."""

from domain.errors import DomainError


class ReorderService:
    def __init__(self, stock_service, supplier_service, purchase_order_service):
        self.stock_service = stock_service
        self.supplier_service = supplier_service
        self.purchase_order_service = purchase_order_service

    def overview(self, product_id=None):
        shortages = self.stock_service.shortages()
        selected = None
        offers = []
        if product_id is not None:
            try:
                product_id = int(product_id)
            except (TypeError, ValueError):
                raise DomainError("Kies een geldig product.")
            selected = next(
                (row for row in shortages if row["product_id"] == product_id),
                None,
            )
            if selected is None:
                raise DomainError("Het product staat niet onder de minimumvoorraad.")
            offers = [
                offer
                for offer in self.supplier_service.offers_for_product(
                    selected["productnaam"]
                )
                if offer["product_id"] == product_id
            ]
        return {"shortages": shortages, "selected": selected, "offers": offers}

    def record_confirmed(self, product_id, supplier_id, quantity, confirmed):
        if confirmed != "yes":
            raise DomainError("Bevestig eerst dat je de fabrikant hebt gesproken.")
        overview = self.overview(product_id)
        try:
            chosen_supplier = int(supplier_id)
        except (TypeError, ValueError):
            raise DomainError("Kies een bestaande leverancier.")
        if not any(
            int(offer["leverancier_id"]) == chosen_supplier
            for offer in overview["offers"]
        ):
            raise DomainError("De leverancier levert het gekozen product niet.")
        return self.purchase_order_service.record_order(
            supplier_id, product_id, quantity, confirmed
        )

    def recorded_orders(self):
        return self.purchase_order_service.recorded_orders()
