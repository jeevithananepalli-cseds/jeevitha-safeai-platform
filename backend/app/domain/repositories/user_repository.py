"""User repository interface (port).

Declared by the domain, implemented by infrastructure. Use cases depend on this
Protocol, never on a concrete database class — the dependency-inversion boundary
that keeps the domain persistence-agnostic and trivially fakeable in tests.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.user import User


class UserRepository(Protocol):
    """Persistence operations for :class:`User`."""

    def add(self, user: User) -> User:
        """Persist a new user and return it with ``id`` and ``created_at`` set."""
        ...

    def get_by_email(self, email: str) -> User | None:
        """Return the user with this (normalized) email, or ``None``."""
        ...

    def get_by_id(self, user_id: int) -> User | None:
        """Return the user with this id, or ``None``."""
        ...
