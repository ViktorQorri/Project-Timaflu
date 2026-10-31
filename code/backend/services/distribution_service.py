"""Business rules for grouping collection bins and releasing packed orders."""

from domain.errors import DomainError


class DistributionService:
    def __init__(self, repository):
        """Create a service that uses the distribution repository.

        Args:
            repository: Repository for orders, sub-orders, bins and packing.
        """
        self.repository = repository

    def orders_with_bins(self):
        """Group collection bins under their customer order.

        Returns:
            A list of orders with their bins, sub-order status and packing actions.
        """
        orders = {}
        for row in self.repository.list_orders_with_bins():
            order_id = row["bestelling_id"]
            order = orders.setdefault(
                order_id,
                {
                    "bestelling_id": order_id,
                    "bedrijfsnaam": row["bedrijfsnaam"],
                    "afleveradres": row["afleveradres"],
                    "gewenste_leverdatum": row["gewenste_leverdatum"],
                    "dagdeel": row["dagdeel"],
                    "spoed": row["spoed"],
                    "status_naam": row["status_naam"],
                    "aantal_verhuisdozen": row["aantal_verhuisdozen"],
                    "bakken": [],
                    "_deelorders": {},
                },
            )
            sub_order_id = row["deelorder_id"]
            if sub_order_id is not None:
                order["_deelorders"][sub_order_id] = bool(row["afgerond"])
            if row["unieke_code"] is not None:
                order["bakken"].append(
                    {
                        "unieke_code": row["unieke_code"],
                        "deelorder_id": sub_order_id,
                        "gang": row["gang"],
                        "afgerond": bool(row["afgerond"]),
                    }
                )

        result = []
        for order in orders.values():
            sub_orders = order.pop("_deelorders")
            all_complete = bool(sub_orders) and all(sub_orders.values())
            order["bestelregels"] = self.repository.list_order_lines(
                order["bestelling_id"]
            )
            order["alle_deelorders_afgerond"] = all_complete
            order["kan_verpakken"] = (
                bool(order["bakken"])
                and all_complete
                and order["status_naam"] not in {
                    "backorder",
                    "ingepakt",
                    "verstuurd",
                    "afgeleverd",
                }
            )
            order["kan_vrijgeven"] = (
                order["status_naam"] == "ingepakt"
                and order["aantal_verhuisdozen"] > 0
            )
            result.append(order)
        return result

    def pack_order(self, order_id, box_count):
        """Validate the order and box count before recording the packing.

        Args:
            order_id: The customer order to pack.
            box_count: Number of moving boxes used.
        """
        order_id = self._positive_integer(order_id, "Bestelling")
        box_count = self._positive_integer(box_count, "Aantal verhuisdozen")
        if box_count > 2_147_483_647:
            raise DomainError("Het aantal verhuisdozen is te groot.")
        self.repository.pack_order(order_id, box_count)

    def release_order(self, order_id):
        """Validate the order identifier before releasing it for distribution.

        Args:
            order_id: The packed customer order to release.
        """
        self.repository.release_order(
            self._positive_integer(order_id, "Bestelling")
        )

    @staticmethod
    def _positive_integer(value, label):
        """Parse a positive database identifier or count."""
        try:
            value = int(value)
        except (TypeError, ValueError) as error:
            raise DomainError(f"{label} moet een positief geheel getal zijn.") from error
        if value < 1:
            raise DomainError(f"{label} moet een positief geheel getal zijn.")
        return value
