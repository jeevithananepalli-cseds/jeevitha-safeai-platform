"""Get-emergency-event use case with owner-only authorization."""

from __future__ import annotations

from app.domain.entities.emergency_event import EmergencyEvent
from app.domain.exceptions import EventNotFoundError
from app.domain.repositories.event_repository import EventRepository


class GetEventUseCase:
    """Fetch a single emergency event, enforcing per-user ownership."""

    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self, user_id: int, event_id: int) -> EmergencyEvent:
        """Return the event if it exists and belongs to the user.

        Raises:
            EventNotFoundError: If the event does not exist *or* is owned by
                another user — the two are indistinguishable to the caller so
                event ids cannot be enumerated (see docs/security-design.md).
        """
        event = self._events.get_by_id(event_id)
        if event is None or event.user_id != user_id:
            raise EventNotFoundError(str(event_id))
        return event
