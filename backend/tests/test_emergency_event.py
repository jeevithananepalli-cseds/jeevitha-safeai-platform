"""Unit tests for the EmergencyEvent entity and its status lifecycle."""

from __future__ import annotations

import pytest

from app.domain.entities.emergency_event import EmergencyEvent, EventStatus
from app.domain.exceptions import InvalidStatusTransitionError
from app.domain.value_objects.coordinates import Coordinates


def _event(status: EventStatus = EventStatus.ACTIVE) -> EmergencyEvent:
    return EmergencyEvent(
        user_id=1,
        event_type="sos",
        location=Coordinates(latitude=17.385, longitude=78.486),
        status=status,
    )


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (EventStatus.ACTIVE, EventStatus.ACKNOWLEDGED),
        (EventStatus.ACTIVE, EventStatus.RESOLVED),
        (EventStatus.ACTIVE, EventStatus.CANCELLED),
        (EventStatus.ACKNOWLEDGED, EventStatus.RESOLVED),
        (EventStatus.ACKNOWLEDGED, EventStatus.CANCELLED),
    ],
)
def test_valid_transitions_are_allowed(start: EventStatus, target: EventStatus) -> None:
    event = _event(start)
    updated = event.with_status(target)
    assert updated.status is target
    # Immutability: the original is unchanged.
    assert event.status is start


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (EventStatus.RESOLVED, EventStatus.ACTIVE),
        (EventStatus.CANCELLED, EventStatus.ACTIVE),
        (EventStatus.RESOLVED, EventStatus.ACKNOWLEDGED),
        (EventStatus.ACTIVE, EventStatus.ACTIVE),
    ],
)
def test_invalid_transitions_are_rejected(start: EventStatus, target: EventStatus) -> None:
    with pytest.raises(InvalidStatusTransitionError):
        _event(start).with_status(target)


def test_can_transition_to_reports_terminal_states() -> None:
    assert _event(EventStatus.ACTIVE).can_transition_to(EventStatus.RESOLVED) is True
    assert _event(EventStatus.RESOLVED).can_transition_to(EventStatus.ACTIVE) is False
