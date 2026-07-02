"""Tests for the LogNotifier's best-effort, per-contact delivery guarantee."""

from __future__ import annotations

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.notifications.log_notifier import LogNotifier


class _FlakyNotifier(LogNotifier):
    """A LogNotifier where delivery to a contact named 'bad' fails."""

    def _deliver(self, event: EmergencyEvent, contact: EmergencyContact) -> None:
        if contact.contact_name == "bad":
            raise RuntimeError("transport failure")
        super()._deliver(event, contact)


def _event() -> EmergencyEvent:
    return EmergencyEvent(user_id=1, event_type="sos", location=Coordinates(0, 0), id=1)


def _contact(name: str, cid: int) -> EmergencyContact:
    return EmergencyContact(user_id=1, contact_name=name, phone_number=f"+199999999{cid}", id=cid)


def test_notifies_every_contact_and_returns_count() -> None:
    notified = LogNotifier().notify(_event(), [_contact("a", 1), _contact("b", 2)])
    assert notified == 2


def test_one_failing_contact_does_not_block_the_others() -> None:
    contacts = [_contact("good1", 1), _contact("bad", 2), _contact("good2", 3)]
    notified = _FlakyNotifier().notify(_event(), contacts)
    # The failing contact is skipped; the other two are still delivered.
    assert notified == 2


def test_notify_with_no_contacts_returns_zero() -> None:
    assert LogNotifier().notify(_event(), []) == 0
