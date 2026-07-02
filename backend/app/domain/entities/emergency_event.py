"""Emergency event domain entity and its status lifecycle.

An ``EmergencyEvent`` is a durable record of an emergency (e.g. an SOS). Its
**status lifecycle** is a domain rule enforced here, not in the API: a resolved
or cancelled event is terminal and cannot be reopened. The entity is immutable —
a status change returns a *new* event (per the project's immutability rule).

Location reuses the framework-free :class:`Coordinates` value object, so an event
can never hold an invalid position.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, replace
from enum import StrEnum

from app.domain.exceptions import InvalidStatusTransitionError
from app.domain.value_objects.coordinates import Coordinates


class EventStatus(StrEnum):
    """Lifecycle states of an emergency event."""

    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


# Allowed forward transitions. Resolved and cancelled are terminal.
_ALLOWED_TRANSITIONS: dict[EventStatus, frozenset[EventStatus]] = {
    EventStatus.ACTIVE: frozenset(
        {EventStatus.ACKNOWLEDGED, EventStatus.RESOLVED, EventStatus.CANCELLED}
    ),
    EventStatus.ACKNOWLEDGED: frozenset({EventStatus.RESOLVED, EventStatus.CANCELLED}),
    EventStatus.RESOLVED: frozenset(),
    EventStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True, slots=True)
class EmergencyEvent:
    """A durable emergency record with a controlled status lifecycle."""

    user_id: int
    event_type: str
    location: Coordinates
    status: EventStatus = EventStatus.ACTIVE
    idempotency_key: str | None = None
    id: int | None = None
    created_at: dt.datetime | None = None
    updated_at: dt.datetime | None = None

    def can_transition_to(self, new_status: EventStatus) -> bool:
        """Return whether moving to ``new_status`` is permitted from the current one."""
        return new_status in _ALLOWED_TRANSITIONS[self.status]

    def with_status(self, new_status: EventStatus) -> EmergencyEvent:
        """Return a new event in ``new_status``.

        Raises:
            InvalidStatusTransitionError: If the transition is not allowed.
        """
        if not self.can_transition_to(new_status):
            msg = f"cannot transition from {self.status.value} to {new_status.value}"
            raise InvalidStatusTransitionError(msg)
        return replace(self, status=new_status)
