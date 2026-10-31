"""Validate scanned picking bins before linking them to a sub-order."""
import re

from domain.errors import DomainError

# Verzamelbak.unieke_code is VARCHAR(50); scanned codes contain letters, digits and dashes.
BIN_CODE = re.compile(r"[A-Za-z0-9_-]{1,50}")
# Same aisles as the CHECK on Magazijnlocatie.gang.
AISLES = ("A", "B", "C", "D", "E", "F", "G", "H")


class PickingBinService:
    def __init__(self, repository):
        self.repository = repository

    def bins(self):
        """Return the registered bins with a readable status per sub-order."""
        return [
            {**row, "status": "Deelorder afgerond" if row["afgerond"] else "Wordt verzameld"}
            for row in self.repository.list_bins()
        ]

    def register(self, bin_code, sub_order_id, aisle):
        """Check the input, then link the bin to the sub-order in the given aisle."""
        # Robots send JSON, so a field can arrive as a number; only text is a valid code or aisle.
        bin_code = bin_code.strip() if isinstance(bin_code, str) else ""
        if not BIN_CODE.fullmatch(bin_code):
            raise DomainError(
                "Vul een bakcode in van maximaal 50 tekens met alleen letters, cijfers, - of _."
            )
        try:
            sub_order_id = int(sub_order_id)
        except (TypeError, ValueError) as error:
            raise DomainError("Het deelordernummer moet een positief geheel getal zijn.") from error
        if sub_order_id < 1:
            raise DomainError("Het deelordernummer moet een positief geheel getal zijn.")
        aisle = aisle.strip().upper() if isinstance(aisle, str) else ""
        if aisle not in AISLES:
            raise DomainError("Kies een gang van A tot en met H.")
        return self.repository.register(bin_code, sub_order_id, aisle)
