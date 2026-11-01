"""Manage customer data centrally for sales, following AD07 Manage customer data."""

from domain.errors import NotFoundError, ValidationError

# Form field, label for messages, maximum length from schema.sql, required.
FIELDS = (
    ("bedrijfsnaam", "Bedrijfsnaam", 100, True),
    ("contactpersoon", "Contactpersoon", 100, False),
    ("telefoonnummer", "Telefoonnummer", 25, False),
    ("afleveradres", "Afleveradres", 255, True),
    ("factuuradres", "Factuuradres", 255, True),
)


class CustomerService:
    def __init__(self, repository):
        self.repository = repository

    def overview(self, search, year):
        """Return all customers, or only those whose name, contact or phone matches the search."""
        return self.repository.list_customers((search or "").strip(), year)

    def get(self, customer_id):
        """Return one customer for the edit or delete screen."""
        customer = self.repository.find_customer(customer_id)
        if customer is None:
            raise NotFoundError("Deze klant bestaat niet.")
        return customer

    def create(self, form):
        """Validate and save a new customer. Returns the new customer number."""
        return self.repository.create(self.validate(form))

    def update(self, customer_id, form):
        """Validate and save changed data of an existing customer."""
        self.repository.update(customer_id, self.validate(form))

    def deactivate(self, customer_id):
        """Deactivate a customer while retaining their history."""
        self.repository.deactivate(customer_id)

    def validate(self, form):
        """Return cleaned customer data, or raise ValidationError with every problem found.

        The phone number is optional in schema.sql; its maximum length is enforced.
        """
        customer, messages = {}, []
        for field, label, max_length, required in FIELDS:
            value = " ".join((form.get(field) or "").split())
            if required and not value:
                messages.append(f"{label} is verplicht.")
            elif len(value) > max_length:
                messages.append(f"{label} mag maximaal {max_length} tekens bevatten.")
            customer[field] = value or None
        if messages:
            raise ValidationError(messages)
        customer["eenmalige_korting_toegezegd"] = form.get("eenmalige_korting_toegezegd") == "on"
        return customer

