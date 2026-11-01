"""Business rules for grouping collection bins and releasing packed orders."""

from datetime import date, time
from decimal import Decimal, InvalidOperation

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

    def orders_to_schedule(self):
        return self.repository.list_orders_to_schedule()

    def couriers(self):
        return self.repository.list_couriers()

    def create_courier(self, name):
        name = str(name or "").strip()
        if not name:
            raise DomainError("Vul de naam van de koerier in.")
        if len(name) > 100:
            raise DomainError("De naam van de koerier mag maximaal 100 tekens bevatten.")
        self.repository.create_courier(name)

    def set_courier_availability(self, courier_id, available):
        if not isinstance(available, bool):
            raise DomainError("Kies of de koerier beschikbaar is.")
        self.repository.set_courier_availability(
            self._positive_integer(courier_id, "Koerier"),
            available,
        )

    def schedule_delivery(self, order_id, courier_id, planned_time):
        if not isinstance(planned_time, time):
            raise DomainError("Kies een geldige bezorgtijd.")
        return self.repository.schedule_delivery(
            self._positive_integer(order_id, "Bestelling"),
            self._positive_integer(courier_id, "Koerier"),
            planned_time,
        )

    def reschedule_failed_delivery(
        self, delivery_id, new_date, part_of_day,
        additional_cost, explanation, customer_contact_confirmed,
    ):
        """Record a replacement appointment after two failed delivery attempts."""
        if customer_contact_confirmed != "yes":
            raise DomainError("Verkoop moet de nieuwe afspraak met de klant bevestigen.")
        delivery_id = self._positive_integer(delivery_id, "Levering")
        try:
            agreed_date = date.fromisoformat(str(new_date or ""))
        except ValueError as error:
            raise DomainError("Kies een geldige nieuwe leverdatum.") from error
        if agreed_date <= date.today():
            raise DomainError("Kies een nieuwe leverdatum na vandaag.")
        if part_of_day not in ("ochtend", "middag"):
            raise DomainError("Kies ochtend of middag voor de nieuwe levering.")
        try:
            costs = Decimal(str(additional_cost or "").replace(",", "."))
        except InvalidOperation as error:
            raise DomainError("Extra bezorgkosten moeten een geldig bedrag zijn.") from error
        if (not costs.is_finite() or costs < 0
                or costs > Decimal("99999999.99")
                or costs != costs.quantize(Decimal("0.01"))):
            raise DomainError("Extra bezorgkosten moeten maximaal twee decimalen hebben.")
        explanation = str(explanation or "").strip()
        if not explanation or len(explanation) > 255:
            raise DomainError("Leg de situatie en eventuele extra kosten kort uit.")
        self.repository.reschedule_failed_delivery(
            delivery_id, agreed_date, part_of_day, costs, explanation
        )
        return agreed_date

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
