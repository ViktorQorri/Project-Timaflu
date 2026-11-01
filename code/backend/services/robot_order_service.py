"""Validate robot-specific operations against the actual aisle assignment."""

from domain.errors import DomainError, NotFoundError


class RobotOrderService:
    def __init__(self, repository):
        self.repository = repository

    @staticmethod
    def _id(value):
        try:
            number = int(value)
        except (ValueError, TypeError):
            raise DomainError("Ongeldig robot- of deelordernummer.")
        if number < 1:
            raise DomainError("Ongeldig robot- of deelordernummer.")
        return number

    def _validate_robot(self, robot_id, aisle):
        robot_id = self._id(robot_id)
        aisle = str(aisle or "").strip().upper()
        if len(aisle) != 1 or aisle not in "ABCDEFGH":
            raise DomainError("Ongeldige magazijngang.")
        if self.repository.robot_for_aisle(robot_id, aisle) is None:
            raise NotFoundError("Geen robot gevonden voor deze gang.")
        return robot_id

    def next_order(self, robot_id, aisle):
        robot_id = self._validate_robot(robot_id, aisle)
        next_order = self.repository.next_suborder(robot_id)
        if not next_order:
            return {"suborder": None, "lines": []}
        return {
            "suborder": next_order,
            "lines": self.repository.suborder_lines(next_order["deelorder_id"]),
        }

    def complete(self, robot_id, aisle, suborder_id, collected):
        """Require the robot to report exactly what was actually collected.

        Counts are in the same package units as the assigned sub-order lines.
        A missing product and a duplicate product are not silently assumed.
        """
        robot_id = self._validate_robot(robot_id, aisle)
        suborder_id = self._id(suborder_id)
        if not isinstance(collected, list) or not collected:
            raise DomainError("Stuur per deelorderregel het werkelijk verzamelde aantal.")
        quantities = {}
        for item in collected:
            if not isinstance(item, dict):
                raise DomainError("Gebruik product_id en quantity per verzameld medicijn.")
            product_id = item.get("product_id")
            quantity = item.get("quantity")
            if (type(product_id) is not int or product_id < 1
                    or type(quantity) is not int or not 0 <= quantity <= 2_147_483_647):
                raise DomainError("Productnummer en verzameld aantal moeten gehele getallen zijn.")
            if product_id in quantities:
                raise DomainError("Een product mag maar eenmaal in het verzamelde resultaat staan.")
            quantities[product_id] = quantity
        return self.repository.complete(robot_id, suborder_id, quantities)

    def generate_suborders(self, order_id):
        """Split a confirmed order from recorded stock reservations."""
        return self.repository.generate(self._id(order_id))
