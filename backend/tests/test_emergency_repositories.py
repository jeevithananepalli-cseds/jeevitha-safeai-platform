"""Integration tests for the emergency repositories against a real SQLite schema.

Foreign keys are enforced (see ``create_db_engine``), so these tests create real
``users`` rows before inserting contacts/events — exactly as PostgreSQL requires.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent, EventStatus
from app.domain.exceptions import EventConflictError
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.db.models.user import UserModel
from app.infrastructure.db.repositories.emergency_contact_repository import (
    SqlAlchemyEmergencyContactRepository,
)
from app.infrastructure.db.repositories.event_repository import SqlAlchemyEventRepository


def _create_user(session: Session, email: str) -> int:
    user = UserModel(name="U", email=email, password_hash="h")
    session.add(user)
    session.flush()
    return user.id


def test_contact_repository_add_list_count(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        u2 = _create_user(session, "u2@example.com")
        repo = SqlAlchemyEmergencyContactRepository(session)
        for i in range(3):
            repo.add(
                EmergencyContact(user_id=u1, contact_name=f"C{i}", phone_number=f"+91987654321{i}")
            )
        repo.add(EmergencyContact(user_id=u2, contact_name="Other", phone_number="+10000000000"))
        session.commit()

        assert repo.count_for_user(u1) == 3
        # Pagination: second page (offset) returns the remaining contact.
        assert len(repo.list_for_user(u1, limit=2, offset=0)) == 2
        assert len(repo.list_for_user(u1, limit=2, offset=2)) == 1
        assert len(repo.all_for_user(u1)) == 3
        assert repo.get_by_user_and_phone(u1, "+919876543210") is not None
        assert repo.get_by_user_and_phone(u1, "+000") is None
    finally:
        session.close()


def test_contact_unique_phone_per_user(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        repo = SqlAlchemyEmergencyContactRepository(session)
        repo.add(EmergencyContact(user_id=u1, contact_name="A", phone_number="+919876543210"))
        session.commit()
        with pytest.raises(IntegrityError):
            repo.add(EmergencyContact(user_id=u1, contact_name="B", phone_number="+919876543210"))
    finally:
        session.rollback()
        session.close()


def test_contact_requires_existing_user_fk(app: FastAPI) -> None:
    # With FK enforcement on, a contact for a non-existent user is rejected
    # (the repository flushes inside add()).
    session = app.state.database.session_factory()
    try:
        repo = SqlAlchemyEmergencyContactRepository(session)
        with pytest.raises(IntegrityError):
            repo.add(
                EmergencyContact(user_id=99999, contact_name="Ghost", phone_number="+10000000000")
            )
    finally:
        session.rollback()
        session.close()


def test_event_repository_round_trips_location_and_status(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        repo = SqlAlchemyEventRepository(session)
        saved = repo.add(
            EmergencyEvent(
                user_id=u1,
                event_type="sos",
                location=Coordinates(latitude=17.385044, longitude=78.486671),
                status=EventStatus.ACTIVE,
                idempotency_key="k1",
            )
        )
        session.commit()
        assert saved.id is not None

        fetched = repo.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.status is EventStatus.ACTIVE
        assert fetched.location.latitude == pytest.approx(17.385044)
        assert fetched.location.longitude == pytest.approx(78.486671)

        by_key = repo.get_by_idempotency_key(u1, "k1")
        assert by_key is not None
        assert by_key.id == saved.id
        assert repo.get_by_idempotency_key(u1, "missing") is None
    finally:
        session.close()


def test_event_duplicate_idempotency_key_raises_conflict(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        u1 = _create_user(session, "u1@example.com")
        repo = SqlAlchemyEventRepository(session)
        repo.add(
            EmergencyEvent(
                user_id=u1, event_type="sos", location=Coordinates(0, 0), idempotency_key="dup"
            )
        )
        session.commit()
        # The repository translates the unique violation into a domain conflict,
        # and the savepoint keeps the session usable afterward.
        with pytest.raises(EventConflictError):
            repo.add(
                EmergencyEvent(
                    user_id=u1, event_type="sos", location=Coordinates(0, 0), idempotency_key="dup"
                )
            )
    finally:
        session.rollback()
        session.close()
