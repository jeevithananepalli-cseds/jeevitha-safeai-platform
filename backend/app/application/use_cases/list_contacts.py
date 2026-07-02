"""List-emergency-contacts use case (paginated)."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.repositories.emergency_contact_repository import EmergencyContactRepository


@dataclass(frozen=True)
class ContactsPage:
    """A page of contacts plus the total count (for pagination metadata)."""

    items: list[EmergencyContact]
    total: int


class ListContactsUseCase:
    """Return a page of a user's emergency contacts.

    Takes plain ``limit``/``offset`` integers so the application layer stays
    independent of the API's pagination types.
    """

    def __init__(self, contacts: EmergencyContactRepository) -> None:
        self._contacts = contacts

    def execute(self, user_id: int, *, limit: int, offset: int) -> ContactsPage:
        items = self._contacts.list_for_user(user_id, limit=limit, offset=offset)
        total = self._contacts.count_for_user(user_id)
        return ContactsPage(items=items, total=total)
