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

    def complete(self, robot_id, aisle, suborder_id):
        robot_id = self._validate_robot(robot_id, aisle)
        return self.repository.complete(robot_id, self._id(suborder_id))

    def generate_suborders(self, order_id):
        """Split a confirmed order from recorded stock reservations."""
        return self.repository.generate(self._id(order_id))
