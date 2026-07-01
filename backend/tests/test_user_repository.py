"""Integration tests for the SQLAlchemy user repository (real SQLite schema)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from app.domain.entities.user import User
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository


def test_add_then_get_by_email_and_id(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        repo = SqlAlchemyUserRepository(session)
        saved = repo.add(User(name="Jeevitha", email="j@example.com", password_hash="h"))
        session.commit()

        assert saved.id is not None
        assert saved.created_at is not None

        by_email = repo.get_by_email("j@example.com")
        assert by_email is not None
        assert by_email.id == saved.id

        by_id = repo.get_by_id(saved.id)
        assert by_id is not None
        assert by_id.email == "j@example.com"

        assert repo.get_by_email("missing@example.com") is None
        assert repo.get_by_id(999999) is None
    finally:
        session.close()


def test_duplicate_email_violates_unique_constraint(app: FastAPI) -> None:
    session = app.state.database.session_factory()
    try:
        repo = SqlAlchemyUserRepository(session)
        repo.add(User(name="A", email="dup@example.com", password_hash="h"))
        session.commit()

        # The unique index on email must reject a second row (flush inside add).
        with pytest.raises(IntegrityError):
            repo.add(User(name="B", email="dup@example.com", password_hash="h"))
    finally:
        session.rollback()
        session.close()
