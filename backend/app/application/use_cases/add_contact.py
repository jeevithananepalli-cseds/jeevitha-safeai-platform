"""Add-emergency-contact use case."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.exceptions import DuplicateContactError
from app.domain.repositories.emergency_contact_repository import EmergencyContactRepository


@dataclass(frozen=True)
class AddContactCommand:
    """Input to :class:`AddContactUseCase`."""

    user_id: int
    contact_name: str
    phone_number: str
    relationship: str | None = None


class AddContactUseCase:
    """Add a trusted emergency contact for a user."""

    def __init__(self, contacts: EmergencyContactRepository) -> None:
        self._contacts = contacts

    def execute(self, command: AddContactCommand) -> EmergencyContact:
        """Add the contact.

        Raises:
            DuplicateContactError: If the user already has this phone number.
        """
        phone = command.phone_number.strip()
        if self._contacts.get_by_user_and_phone(command.user_id, phone) is not None:
            raise DuplicateContactError(phone)

        contact = EmergencyContact(
            user_id=command.user_id,
            contact_name=command.contact_name.strip(),
            phone_number=phone,
            relationship=command.relationship,
        )
        return self._contacts.add(contact)
