"""SQLAlchemy implementation of the ``LocationRepository`` port."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.entities.location_sample import LocationSample
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.db.models.location_history import LocationHistoryModel


class SqlAlchemyLocationRepository:
    """Persist and load location samples. Implements the domain port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, sample: LocationSample) -> LocationSample:
        model = LocationHistoryModel(
            user_id=sample.user_id,
            latitude=sample.location.latitude,
            longitude=sample.location.longitude,
        )
        self._session.add(model)
        self._session.flush()
        return self._to_entity(model)

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[LocationSample]:
        rows = self._session.scalars(
            select(LocationHistoryModel)
            .where(LocationHistoryModel.user_id == user_id)
            # Newest first; id as a tiebreaker for samples in the same instant
            # (keeps pagination stable and deterministic).
            .order_by(LocationHistoryModel.recorded_at.desc(), LocationHistoryModel.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return [self._to_entity(row) for row in rows]

    def count_for_user(self, user_id: int) -> int:
        total = self._session.scalar(
            select(func.count())
            .select_from(LocationHistoryModel)
            .where(LocationHistoryModel.user_id == user_id)
        )
        return total or 0

    @staticmethod
    def _to_entity(model: LocationHistoryModel) -> LocationSample:
        return LocationSample(
            id=model.id,
            user_id=model.user_id,
            location=Coordinates(latitude=model.latitude, longitude=model.longitude),
            recorded_at=model.recorded_at,
        )
