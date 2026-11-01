"""Business validation for reservation operations."""
from domain.errors import DomainError


class ReservationService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _ids(order_id, product_id):
        try:
            values = int(order_id), int(product_id)
        except (TypeError, ValueError) as error:
            raise DomainError("Order en product moeten hele getallen zijn.") from error
        if any(value < 1 for value in values):
            raise DomainError("Order en product moeten groter dan 0 zijn.")
        return values

    def reserve_confirmed_line(self, order_id, product_id):
        return self.repository.reserve_existing_line(*self._ids(order_id, product_id))

    def release_line(self, order_id, product_id):
        return self.repository.release_existing_line(*self._ids(order_id, product_id))
