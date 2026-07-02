"""Update-event-status use case — drives the emergency event lifecycle.

Completes the workflow started by ``TriggerSosUseCase``: an active emergency is
acknowledged, then resolved (or cancelled). The transition rules live in the
domain entity (``EmergencyEvent.with_status``); this use case adds the
authorization rule (owner-only, with not-owned indistinguishable from missing)
and persistence.
"""

from __future__ import annotations

from app.domain.entities.emergency_event import EmergencyEvent, EventStatus
from app.domain.exceptions import EventNotFoundError
from app.domain.repositories.event_repository import EventRepository


class UpdateEventStatusUseCase:
    """Transition one of the user's emergency events to a new status."""

    def __init__(self, events: EventRepository) -> None:
        self._events = events

    def execute(self, user_id: int, event_id: int, new_status: EventStatus) -> EmergencyEvent:
        """Apply the transition and persist it.

        Raises:
            EventNotFoundError: If the event does not exist or belongs to
                another user (indistinguishable, to prevent id enumeration).
            InvalidStatusTransitionError: If the lifecycle forbids the change
                (raised by the domain entity).
        """
        event = self._events.get_by_id(event_id)
        if event is None or event.user_id != user_id:
            raise EventNotFoundError(str(event_id))

        updated = event.with_status(new_status)
        return self._events.update_status(updated)
