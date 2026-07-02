"""Trigger-SOS use case — the heart of the emergency workflow.

Two guarantees make this correct and safe:

* **Write-first, notify-after.** The event is durably persisted *before* any
  notification is attempted, so a real emergency is never lost if delivery fails.
* **Idempotency.** A client may retry (or a panicked user may double-tap). When
  an ``Idempotency-Key`` is supplied, a repeat returns the *same* event instead
  of creating a second one or re-notifying contacts.

See docs/architecture.md §4 and docs/glossary.md → *Idempotency*.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.emergency_event import EmergencyEvent, EventStatus
from app.domain.exceptions import EventConflictError
from app.domain.repositories.emergency_contact_repository import EmergencyContactRepository
from app.domain.repositories.event_repository import EventRepository
from app.domain.services.notifier import Notifier
from app.domain.value_objects.coordinates import Coordinates


@dataclass(frozen=True)
class TriggerSosCommand:
    """Input to :class:`TriggerSosUseCase`."""

    user_id: int
    event_type: str
    location: Coordinates
    idempotency_key: str | None = None


@dataclass(frozen=True)
class SosResult:
    """Outcome of triggering an SOS."""

    event: EmergencyEvent
    notified_contacts: int
    created: bool  # False when an idempotent replay returned an existing event


class TriggerSosUseCase:
    """Create an emergency event and notify the user's contacts."""

    def __init__(
        self,
        events: EventRepository,
        contacts: EmergencyContactRepository,
        notifier: Notifier,
    ) -> None:
        self._events = events
        self._contacts = contacts
        self._notifier = notifier

    def execute(self, command: TriggerSosCommand) -> SosResult:
        # Idempotent replay: return the existing event, do not re-create/re-notify.
        if command.idempotency_key is not None:
            existing = self._events.get_by_idempotency_key(command.user_id, command.idempotency_key)
            if existing is not None:
                return SosResult(event=existing, notified_contacts=0, created=False)

        event = EmergencyEvent(
            user_id=command.user_id,
            event_type=command.event_type,
            location=command.location,
            status=EventStatus.ACTIVE,
            idempotency_key=command.idempotency_key,
        )

        # 1) Persist first — the emergency record must survive a notify failure.
        try:
            persisted = self._events.add(event)
        except EventConflictError:
            # Lost an idempotency race: a concurrent request created this event
            # first. Return the existing one as a replay instead of erroring.
            replayed = self._replay_or_none(command)
            if replayed is not None:
                return replayed
            raise

        # 2) Notify afterward — best-effort, independent per contact.
        contacts = self._contacts.all_for_user(command.user_id)
        notified = self._notifier.notify(persisted, contacts)

        return SosResult(event=persisted, notified_contacts=notified, created=True)

    def _replay_or_none(self, command: TriggerSosCommand) -> SosResult | None:
        """Return the existing event for this idempotency key as a replay, if any."""
        if command.idempotency_key is None:
            return None
        existing = self._events.get_by_idempotency_key(command.user_id, command.idempotency_key)
        if existing is None:
            return None
        return SosResult(event=existing, notified_contacts=0, created=False)
