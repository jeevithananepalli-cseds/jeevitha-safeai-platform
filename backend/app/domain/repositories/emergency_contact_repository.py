"""Emergency contact repository interface (port)."""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.emergency_contact import EmergencyContact


class EmergencyContactRepository(Protocol):
    """Persistence operations for :class:`EmergencyContact`."""

    def add(self, contact: EmergencyContact) -> EmergencyContact:
        """Persist a new contact and return it with ``id`` set."""
        ...

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[EmergencyContact]:
        """Return a page of a user's contacts (stable order)."""
        ...

    def all_for_user(self, user_id: int) -> list[EmergencyContact]:
        """Return all of a user's contacts (used to fan out SOS notifications)."""
        ...

    def count_for_user(self, user_id: int) -> int:
        """Return the total number of a user's contacts (for pagination meta)."""
        ...

    def get_by_user_and_phone(self, user_id: int, phone_number: str) -> EmergencyContact | None:
        """Return a user's contact with this phone number, or ``None``."""
        ...
