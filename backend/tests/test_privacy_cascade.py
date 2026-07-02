"""Tests for the privacy guarantees around account deletion.

docs/security-design.md §7 promises that a user's personal data (contacts,
events, location history) cascades away with the account. With foreign-key
enforcement active on SQLite, these tests prove the guarantee end-to-end —
including that a still-valid JWT for a deleted account is rejected.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent
from app.domain.entities.location_sample import LocationSample
from app.domain.value_objects.coordinates import Coordinates
from app.infrastructure.db.models.emergency_contact import EmergencyContactModel
from app.infrastructure.db.models.emergency_event import EmergencyEventModel
from app.infrastructure.db.models.location_history import LocationHistoryModel
from app.infrastructure.db.models.user import UserModel
from app.infrastructure.db.repositories.emergency_contact_repository import (
    SqlAlchemyEmergencyContactRepository,
)
from app.infrastructure.db.repositories.event_repository import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.location_repository import SqlAlchemyLocationRepository


def test_deleting_a_user_cascades_all_personal_data(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        # Arrange: a user with one contact, one event, and one location sample.
        user = UserModel(name="U", email="cascade@example.com", password_hash="h")
        session.add(user)
        session.flush()

        SqlAlchemyEmergencyContactRepository(session).add(
            EmergencyContact(user_id=user.id, contact_name="A", phone_number="+919876543210")
        )
        SqlAlchemyEventRepository(session).add(
            EmergencyEvent(user_id=user.id, event_type="sos", location=Coordinates(1, 2))
        )
        SqlAlchemyLocationRepository(session).add(
            LocationSample(user_id=user.id, location=Coordinates(3, 4))
        )
        session.commit()

        # Act: delete the account.
        session.delete(session.get(UserModel, user.id))
        session.commit()

        # Assert: every owned row is gone (the privacy cascade).
        for model in (EmergencyContactModel, EmergencyEventModel, LocationHistoryModel):
            remaining = session.scalar(select(func.count()).select_from(model))
            assert remaining == 0, f"{model.__tablename__} rows survived user deletion"
    finally:
        session.close()


def test_valid_token_for_deleted_user_is_rejected(
    app: FastAPI, client: TestClient, auth_headers: dict[str, str]
) -> None:
    # The token is currently valid...
    assert client.get("/api/v1/profile", headers=auth_headers).status_code == 200

    # ...then the account is deleted (token itself remains cryptographically valid).
    session = app.state.database.session_factory()
    try:
        user = session.scalars(
            select(UserModel).where(UserModel.email == "fixture-user@example.com")
        ).one()
        session.delete(user)
        session.commit()
    finally:
        session.close()

    # A deleted account's token must no longer grant access.
    response = client.get("/api/v1/profile", headers=auth_headers)
    assert response.status_code == 401
