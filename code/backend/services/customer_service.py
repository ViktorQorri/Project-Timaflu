"""Manage customer data centrally for sales, following AD07 Manage customer data."""

import re

from domain.errors import NotFoundError, ValidationError

# Form field, label for messages, maximum length from schema.sql, required.
FIELDS = (
    ("bedrijfsnaam", "Bedrijfsnaam", 100, True),
    ("contactpersoon", "Contactpersoon", 100, False),
    ("telefoonnummer", "Telefoonnummer", 25, True),
    ("afleveradres", "Afleveradres", 255, True),
    ("factuuradres", "Factuuradres", 255, True),
)
PHONE_CHARACTERS = re.compile(r"\+?[0-9 ()-]+")
MIN_PHONE_DIGITS = 8


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

    def delete(self, customer_id):
        """Delete a customer; customers with history are refused by the repository."""
        self.repository.delete(customer_id)

    def validate(self, form):
        """Return cleaned customer data, or raise ValidationError with every problem found.

        The phone number is required so couriers can call the customer (AD15).
        """
        customer, messages = {}, []
        for field, label, max_length, required in FIELDS:
            value = " ".join((form.get(field) or "").split())
            if required and not value:
                messages.append(f"{label} is verplicht.")
            elif len(value) > max_length:
                messages.append(f"{label} mag maximaal {max_length} tekens bevatten.")
            customer[field] = value or None
        phone = customer["telefoonnummer"]
        if phone and not self._is_phone_number(phone):
            messages.append(
                f"Telefoonnummer mag alleen cijfers, spaties, +, - en haakjes bevatten "
                f"en moet minstens {MIN_PHONE_DIGITS} cijfers hebben."
            )
        if messages:
            raise ValidationError(messages)
        return customer

    @staticmethod
    def _is_phone_number(value):
        digits = sum(character.isdigit() for character in value)
        return PHONE_CHARACTERS.fullmatch(value) is not None and digits >= MIN_PHONE_DIGITS
