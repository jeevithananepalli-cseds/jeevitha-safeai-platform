"""Emergency event repository interface (port)."""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.emergency_event import EmergencyEvent


class EventRepository(Protocol):
    """Persistence operations for :class:`EmergencyEvent`."""

    def add(self, event: EmergencyEvent) -> EmergencyEvent:
        """Persist a new event and return it with ``id``/timestamps set."""
        ...

    def get_by_id(self, event_id: int) -> EmergencyEvent | None:
        """Return the event with this id, or ``None``."""
        ...

    def get_by_idempotency_key(self, user_id: int, idempotency_key: str) -> EmergencyEvent | None:
        """Return this user's event previously created with the given
        idempotency key, or ``None`` — the basis for idempotent SOS creation."""
        ...

    def update_status(self, event: EmergencyEvent) -> EmergencyEvent:
        """Persist ``event``'s status (the event must already exist) and return
        the stored entity with a refreshed ``updated_at``."""
        ...
