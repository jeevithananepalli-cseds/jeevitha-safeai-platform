"""SQLAlchemy implementation of the ``UserRepository`` port.

Owns all ORM/SQL detail and translates between the persistence model
(``UserModel``) and the framework-free domain entity (``User``). Transaction
control is *not* here — the request-scoped session (see ``app.api.deps``) is the
unit of work and commits once per successful request.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.entities.user import User
from app.infrastructure.db.models.user import UserModel


class SqlAlchemyUserRepository:
    """Persist and load users via SQLAlchemy. Implements ``UserRepository``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, user: User) -> User:
        model = UserModel(
            name=user.name,
            email=user.email,
            password_hash=user.password_hash,
        )
        self._session.add(model)
        # Flush to assign the primary key and populate defaults without ending
        # the transaction (the request's commit happens at session teardown).
        self._session.flush()
        return self._to_entity(model)

    def get_by_email(self, email: str) -> User | None:
        model = self._session.scalars(
            select(UserModel).where(UserModel.email == email)
        ).one_or_none()
        return self._to_entity(model) if model is not None else None

    def get_by_id(self, user_id: int) -> User | None:
        model = self._session.get(UserModel, user_id)
        return self._to_entity(model) if model is not None else None

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            name=model.name,
            email=model.email,
            password_hash=model.password_hash,
            created_at=model.created_at,
        )
