"""Validate acquisition visits and follow-up outcomes."""

from datetime import date

from domain.errors import DomainError


class AcquisitionService:
    def __init__(self, repository):
        """Create a service that uses the acquisition repository.

        Args:
            repository: Repository for prospects, visits and customer conversion.
        """
        self.repository = repository

    def due_follow_ups(self):
        """Return prospects ready for a follow-up visit or call."""
        return self.repository.find_due_follow_ups()

    def register_prospect(self, form):
        """Validate and save a prospect and the date of the acquisition visit.

        Args:
            form: Submitted form values.

        Returns:
            The new prospective-customer identifier.
        """
        prospect = {
            "company_name": self._required_text(form, "company_name", "Bedrijfsnaam", 100),
            "contact_person": self._required_text(
                form, "contact_person", "Contactpersoon", 100
            ),
            "contact_details": self._required_text(
                form, "contact_details", "Contactgegevens", 255
            ),
            "address": self._required_text(form, "address", "Adres", 255),
        }
        visit_value = (form.get("visit_date") or "").strip()
        try:
            prospect["visit_date"] = date.fromisoformat(visit_value)
        except (TypeError, ValueError) as error:
            raise DomainError("Vul een geldige bezoekdatum in.") from error
        return self.repository.register_prospect(prospect)

    def complete_follow_up(self, prospect_id, form):
        """Validate a follow-up decision and optionally create a customer account.

        Args:
            prospect_id: The prospect identifier from the route.
            form: Submitted outcome and, when converting, customer details.

        Returns:
            The created customer identifier, or None when no account was created.
        """
        try:
            prospect_id = int(prospect_id)
        except (TypeError, ValueError) as error:
            raise DomainError("Potentiële klant moet een positief geheel getal zijn.") from error
        if prospect_id < 1:
            raise DomainError("Potentiële klant moet een positief geheel getal zijn.")

        outcome = (form.get("outcome") or "").strip()
        if outcome not in {"convert", "no_interest", "no_consent"}:
            raise DomainError("Kies een geldige opvolguitkomst.")
        if outcome != "convert":
            return self.repository.complete_follow_up(prospect_id, outcome)

        customer = {
            "delivery_address": self._required_text(
                form, "delivery_address", "Afleveradres", 255
            ),
            "invoice_address": self._required_text(
                form, "invoice_address", "Factuuradres", 255
            ),
            "phone_number": self._optional_text(form, "phone_number", "Telefoonnummer", 25),
        }
        return self.repository.complete_follow_up(prospect_id, outcome, customer)

    @staticmethod
    def _required_text(form, field, label, maximum):
        """Return a trimmed required field after enforcing its database length."""
        value = (form.get(field) or "").strip()
        if not value:
            raise DomainError(f"Vul {label.lower()} in.")
        if len(value) > maximum:
            raise DomainError(f"{label} mag maximaal {maximum} tekens bevatten.")
        return value

    @staticmethod
    def _optional_text(form, field, label, maximum):
        """Return an optional trimmed field after enforcing its database length."""
        value = (form.get(field) or "").strip()
        if len(value) > maximum:
            raise DomainError(f"{label} mag maximaal {maximum} tekens bevatten.")
        return value or None
