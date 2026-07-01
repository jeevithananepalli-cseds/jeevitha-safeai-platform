"""In-memory fakes implementing the domain ports.

These let the use cases be unit-tested with zero database and zero bcrypt cost,
demonstrating that the application layer depends only on interfaces.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

from app.domain.entities.user import User


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
