"""Unit tests for the emergency use cases (in-memory fakes, no DB)."""

from __future__ import annotations

import pytest

from app.application.use_cases.add_contact import AddContactCommand, AddContactUseCase
from app.application.use_cases.get_event import GetEventUseCase
from app.application.use_cases.list_contacts import ListContactsUseCase
from app.application.use_cases.trigger_sos import TriggerSosCommand, TriggerSosUseCase
from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent, EventStatus
from app.domain.exceptions import DuplicateContactError, EventConflictError, EventNotFoundError
from app.domain.value_objects.coordinates import Coordinates
from tests.fakes import (
    InMemoryEmergencyContactRepository,
    InMemoryEventRepository,
    RecordingNotifier,
)

LOCATION = Coordinates(latitude=17.385, longitude=78.486)


# --- add / list contacts ------------------------------------------------------


def test_add_contact_persists_and_returns_with_id() -> None:
    repo = InMemoryEmergencyContactRepository()
    contact = AddContactUseCase(repo).execute(
        AddContactCommand(
            user_id=1, contact_name="Amma", phone_number="+919876543210", relationship="parent"
        )
    )
    assert contact.id is not None
    assert repo.count_for_user(1) == 1


def test_add_contact_rejects_duplicate_phone_for_same_user() -> None:
    repo = InMemoryEmergencyContactRepository()
    use_case = AddContactUseCase(repo)
    use_case.execute(
        AddContactCommand(user_id=1, contact_name="Amma", phone_number="+919876543210")
    )
    with pytest.raises(DuplicateContactError):
        use_case.execute(
            AddContactCommand(user_id=1, contact_name="Amma2", phone_number="+919876543210")
        )


def test_list_contacts_returns_page_and_total() -> None:
    repo = InMemoryEmergencyContactRepository()
    for i in range(3):
        repo.add(EmergencyContact(user_id=1, contact_name=f"C{i}", phone_number=f"+91987654321{i}"))
    repo.add(EmergencyContact(user_id=2, contact_name="Other", phone_number="+10000000000"))

    page = ListContactsUseCase(repo).execute(1, limit=2, offset=0)
    assert page.total == 3  # only user 1's contacts
    assert len(page.items) == 2  # limited


# --- trigger SOS --------------------------------------------------------------


def _sos_setup() -> tuple[list[str], InMemoryEventRepository, TriggerSosUseCase]:
    call_log: list[str] = []
    events = InMemoryEventRepository(call_log)
    contacts = InMemoryEmergencyContactRepository()
    contacts.add(EmergencyContact(user_id=1, contact_name="A", phone_number="+919876543210"))
    contacts.add(EmergencyContact(user_id=1, contact_name="B", phone_number="+919876543211"))
    notifier = RecordingNotifier(call_log)
    return call_log, events, TriggerSosUseCase(events, contacts, notifier)


def test_sos_creates_active_event_and_notifies_all_contacts() -> None:
    _call_log, _events, use_case = _sos_setup()
    result = use_case.execute(
        TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="k1")
    )
    assert result.created is True
    assert result.event.status is EventStatus.ACTIVE
    assert result.event.id is not None
    assert result.notified_contacts == 2


def test_sos_persists_before_notifying() -> None:
    call_log, _events, use_case = _sos_setup()
    use_case.execute(TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION))
    # The durable write must happen before any notification attempt.
    assert call_log == ["persist", "notify"]


def test_sos_is_idempotent_for_repeated_key() -> None:
    call_log, _events, use_case = _sos_setup()
    first = use_case.execute(
        TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="dup")
    )
    second = use_case.execute(
        TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="dup")
    )
    assert second.created is False
    assert second.event.id == first.event.id
    assert second.notified_contacts == 0
    # Exactly one persist and one notify occurred across both calls.
    assert call_log == ["persist", "notify"]


def test_sos_with_different_key_creates_new_event() -> None:
    _call_log, _events, use_case = _sos_setup()
    first = use_case.execute(
        TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="a")
    )
    second = use_case.execute(
        TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="b")
    )
    assert second.created is True
    assert second.event.id != first.event.id


class _RacingEventRepository:
    """Simulates losing an idempotency race: ``add`` conflicts, and the winning
    event is (optionally) retrievable by key afterward."""

    def __init__(self, winner: EmergencyEvent | None) -> None:
        self._winner = winner
        self._key_lookups = 0

    def get_by_idempotency_key(self, user_id: int, key: str) -> EmergencyEvent | None:
        self._key_lookups += 1
        # First lookup is the pre-check (miss); later lookups return the winner.
        return None if self._key_lookups == 1 else self._winner

    def add(self, event: EmergencyEvent) -> EmergencyEvent:
        raise EventConflictError("race")

    def get_by_id(self, event_id: int) -> EmergencyEvent | None:  # pragma: no cover - unused here
        return None


def test_sos_recovers_from_idempotency_race_as_replay() -> None:
    winner = EmergencyEvent(
        user_id=1, event_type="sos", location=LOCATION, idempotency_key="k", id=42
    )
    use_case = TriggerSosUseCase(
        _RacingEventRepository(winner), InMemoryEmergencyContactRepository(), RecordingNotifier()
    )
    result = use_case.execute(
        TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="k")
    )
    assert result.created is False
    assert result.event.id == 42
    assert result.notified_contacts == 0


def test_sos_reraises_conflict_when_winner_not_found() -> None:
    use_case = TriggerSosUseCase(
        _RacingEventRepository(None), InMemoryEmergencyContactRepository(), RecordingNotifier()
    )
    with pytest.raises(EventConflictError):
        use_case.execute(
            TriggerSosCommand(user_id=1, event_type="sos", location=LOCATION, idempotency_key="k")
        )


# --- get event (authorization) ------------------------------------------------


def test_get_event_returns_owned_event() -> None:
    events = InMemoryEventRepository()
    saved = events.add(EmergencyEvent(user_id=1, event_type="sos", location=LOCATION))
    assert saved.id is not None

    fetched = GetEventUseCase(events).execute(1, saved.id)
    assert fetched.id == saved.id


def test_get_event_hides_other_users_event_as_not_found() -> None:
    events = InMemoryEventRepository()
    saved = events.add(EmergencyEvent(user_id=1, event_type="sos", location=LOCATION))
    assert saved.id is not None

    with pytest.raises(EventNotFoundError):
        GetEventUseCase(events).execute(2, saved.id)  # different user


def test_get_event_raises_for_unknown_id() -> None:
    with pytest.raises(EventNotFoundError):
        GetEventUseCase(InMemoryEventRepository()).execute(1, 999999)
