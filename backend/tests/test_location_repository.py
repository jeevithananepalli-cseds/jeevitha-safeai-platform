"""Integration tests for the SQLAlchemy location repository (real schema, FKs on)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities.location_sample import LocationSample
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.db.models.user import UserModel
from app.infrastructure.db.repositories.location_repository import SqlAlchemyLocationRepository


def _create_user(session: Session, email: str) -> int:
    user = UserModel(name="U", email=email, password_hash="h")
    session.add(user)
    session.flush()
    return user.id


def _sample(user_id: int, lat: float) -> LocationSample:
    return LocationSample(user_id=user_id, location=Coordinates(latitude=lat, longitude=0))


def test_add_and_list_newest_first_with_stable_tiebreak(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        repo = SqlAlchemyLocationRepository(session)
        for lat in (1.0, 2.0, 3.0):  # inserted in this order
            saved = repo.add(_sample(u1, lat))
            assert saved.id is not None
            assert saved.recorded_at is not None
        session.commit()

        # Same-instant samples fall back to id DESC — newest insert first.
        page1 = repo.list_for_user(u1, limit=2, offset=0)
        assert [s.location.latitude for s in page1] == [3.0, 2.0]
        page2 = repo.list_for_user(u1, limit=2, offset=2)
        assert [s.location.latitude for s in page2] == [1.0]
        assert repo.count_for_user(u1) == 3
    finally:
        session.close()


def test_history_is_isolated_per_user(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        u2 = _create_user(session, "u2@example.com")
        repo = SqlAlchemyLocationRepository(session)
        repo.add(_sample(u1, 1.0))
        repo.add(_sample(u2, 2.0))
        session.commit()

        assert repo.count_for_user(u1) == 1
        assert repo.list_for_user(u1, limit=10, offset=0)[0].location.latitude == 1.0
    finally:
        session.close()


def test_location_requires_existing_user_fk(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        repo = SqlAlchemyLocationRepository(session)
        with pytest.raises(IntegrityError):
            repo.add(_sample(99999, 0.0))
    finally:
        session.rollback()
        session.close()


def test_coordinates_round_trip_precision(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        repo = SqlAlchemyLocationRepository(session)
        saved = repo.add(
            LocationSample(
                user_id=u1, location=Coordinates(latitude=17.385044, longitude=78.486671)
            )
        )
        session.commit()
        assert saved.id is not None

        fetched = repo.list_for_user(u1, limit=1, offset=0)[0]
        assert fetched.location.latitude == pytest.approx(17.385044)
        assert fetched.location.longitude == pytest.approx(78.486671)
    finally:
        session.close()
