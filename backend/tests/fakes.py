"""In-memory fakes implementing the domain ports.

These let the use cases be unit-tested with zero database and zero bcrypt cost,
demonstrating that the application layer depends only on interfaces.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent
from app.domain.entities.location_sample import LocationSample
from app.domain.entities.user import User


def _utcnow() -> dt.datetime:
    return dt.datetime.now(tz=dt.UTC)


class InMemoryUserRepository:
    """A dict-backed ``UserRepository`` for fast, isolated unit tests."""

    def __init__(self) -> None:
        self._users: dict[int, User] = {}
        self._next_id = 1

    def add(self, user: User) -> User:
        stored = replace(user, id=self._next_id, created_at=dt.datetime.now(tz=dt.UTC))
        self._users[self._next_id] = stored
        self._next_id += 1
        return stored

    def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._users.values() if u.email == email), None)

    def get_by_id(self, user_id: int) -> User | None:
        return self._users.get(user_id)


class FakeHasher:
    """A trivial, deterministic ``PasswordHasher`` — never use in production."""

    def hash(self, password: str) -> str:
        return f"hashed::{password}"

    def verify(self, password: str, password_hash: str) -> bool:
        return password_hash == f"hashed::{password}"


class InMemoryEmergencyContactRepository:
    """A dict-backed ``EmergencyContactRepository`` for unit tests."""

    def __init__(self) -> None:
        self._items: dict[int, EmergencyContact] = {}
        self._next_id = 1

    def add(self, contact: EmergencyContact) -> EmergencyContact:
        stored = replace(contact, id=self._next_id)
        self._items[self._next_id] = stored
        self._next_id += 1
        return stored

    def _sorted_for_user(self, user_id: int) -> list[EmergencyContact]:
        items = [c for c in self._items.values() if c.user_id == user_id]
        return sorted(items, key=lambda c: c.id or 0)

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[EmergencyContact]:
        return self._sorted_for_user(user_id)[offset : offset + limit]

    def all_for_user(self, user_id: int) -> list[EmergencyContact]:
        return self._sorted_for_user(user_id)

    def count_for_user(self, user_id: int) -> int:
        return len(self._sorted_for_user(user_id))

    def get_by_user_and_phone(self, user_id: int, phone_number: str) -> EmergencyContact | None:
        return next(
            (
                c
                for c in self._items.values()
                if c.user_id == user_id and c.phone_number == phone_number
            ),
            None,
        )


class InMemoryEventRepository:
    """A dict-backed ``EventRepository``.

    Records each ``add`` into a shared ``call_log`` so tests can assert the SOS
    use case persists *before* notifying.
    """

    def __init__(self, call_log: list[str] | None = None) -> None:
        self._items: dict[int, EmergencyEvent] = {}
        self._next_id = 1
        self.call_log = call_log if call_log is not None else []

    def add(self, event: EmergencyEvent) -> EmergencyEvent:
        self.call_log.append("persist")
        stored = replace(event, id=self._next_id, created_at=_utcnow(), updated_at=_utcnow())
        self._items[self._next_id] = stored
        self._next_id += 1
        return stored

    def get_by_id(self, event_id: int) -> EmergencyEvent | None:
        return self._items.get(event_id)

    def get_by_idempotency_key(self, user_id: int, idempotency_key: str) -> EmergencyEvent | None:
        return next(
            (
                e
                for e in self._items.values()
                if e.user_id == user_id and e.idempotency_key == idempotency_key
            ),
            None,
        )

    def update_status(self, event: EmergencyEvent) -> EmergencyEvent:
        assert event.id is not None
        stored = replace(event, updated_at=_utcnow())
        self._items[event.id] = stored
        return stored


class InMemoryLocationRepository:
    """A dict-backed ``LocationRepository`` for unit tests (newest first)."""

    def __init__(self) -> None:
        self._items: dict[int, LocationSample] = {}
        self._next_id = 1

    def add(self, sample: LocationSample) -> LocationSample:
        stored = replace(sample, id=self._next_id, recorded_at=_utcnow())
        self._items[self._next_id] = stored
        self._next_id += 1
        return stored

    def _newest_first(self, user_id: int) -> list[LocationSample]:
        items = [s for s in self._items.values() if s.user_id == user_id]
        # recorded_at can collide within a test; id order mirrors insert order.
        return sorted(items, key=lambda s: s.id or 0, reverse=True)

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[LocationSample]:
        return self._newest_first(user_id)[offset : offset + limit]

    def count_for_user(self, user_id: int) -> int:
        return len(self._newest_first(user_id))


class RecordingNotifier:
    """A ``Notifier`` that records invocation order and returns the count."""

    def __init__(self, call_log: list[str] | None = None) -> None:
        self.call_log = call_log if call_log is not None else []
        self.notified_counts: list[int] = []

    def notify(self, event: EmergencyEvent, contacts: list[EmergencyContact]) -> int:
        self.call_log.append("notify")
        self.notified_counts.append(len(contacts))
        return len(contacts)
