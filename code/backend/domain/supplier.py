from dataclasses import dataclass


@dataclass
class Supplier:
    """A manufacturer Timaflu buys medicines from."""

    supplier_id: int
    name: str
    contact_person: str | None
    phone_number: str | None
    website: str | None
