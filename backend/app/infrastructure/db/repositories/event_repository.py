"""SQLAlchemy implementation of the ``EventRepository`` port.

Maps between the ``emergency_events`` row and the domain ``EmergencyEvent`` —
translating the stored ``latitude``/``longitude`` into the ``Coordinates`` value
object and the stored status string into the ``EventStatus`` enum.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities.emergency_event import EmergencyEvent, EventStatus
from app.domain.exceptions import EventConflictError
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.db.models.emergency_event import EmergencyEventModel


class SqlAlchemyEventRepository:
    """Persist and load emergency events. Implements the domain port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, event: EmergencyEvent) -> EmergencyEvent:
        model = EmergencyEventModel(
            user_id=event.user_id,
            event_type=event.event_type,
            latitude=event.location.latitude,
            longitude=event.location.longitude,
            status=event.status.value,
            idempotency_key=event.idempotency_key,
        )
        # Insert inside a SAVEPOINT: if the per-user idempotency unique constraint
        # is violated (a concurrent SOS won the race), the savepoint rolls back
        # without poisoning the outer transaction, and we surface a domain
        # conflict the SOS use case can recover from as an idempotent replay.
        try:
            with self._session.begin_nested():
                self._session.add(model)
                self._session.flush()
        except IntegrityError as exc:
            raise EventConflictError(str(event.idempotency_key)) from exc
        return self._to_entity(model)

    def get_by_id(self, event_id: int) -> EmergencyEvent | None:
        model = self._session.get(EmergencyEventModel, event_id)
        return self._to_entity(model) if model is not None else None

    def get_by_idempotency_key(self, user_id: int, idempotency_key: str) -> EmergencyEvent | None:
        model = self._session.scalars(
            select(EmergencyEventModel)
            .where(EmergencyEventModel.user_id == user_id)
            .where(EmergencyEventModel.idempotency_key == idempotency_key)
        ).one_or_none()
        return self._to_entity(model) if model is not None else None

    def update_status(self, event: EmergencyEvent) -> EmergencyEvent:
        if event.id is None:  # pragma: no cover - guarded by the use case
            msg = "cannot update an unpersisted event"
            raise ValueError(msg)
        model = self._session.get(EmergencyEventModel, event.id)
        if model is None:  # pragma: no cover - guarded by the use case
            msg = f"event {event.id} not found"
            raise ValueError(msg)
        model.status = event.status.value
        # Flush so `onupdate` refreshes updated_at and the entity we return
        # reflects the stored row.
        self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: EmergencyEventModel) -> EmergencyEvent:
        return EmergencyEvent(
            id=model.id,
            user_id=model.user_id,
            event_type=model.event_type,
            location=Coordinates(latitude=model.latitude, longitude=model.longitude),
            status=EventStatus(model.status),
            idempotency_key=model.idempotency_key,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
