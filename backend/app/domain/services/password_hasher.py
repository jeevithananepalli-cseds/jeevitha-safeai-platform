"""Password hasher interface (port).

The use cases depend on this abstraction rather than on bcrypt directly, so the
hashing implementation is swappable and unit tests can inject a trivial fake.
The concrete bcrypt adapter lives in ``app.infrastructure.security``.
"""

from __future__ import annotations

from typing import Protocol


class PasswordHasher(Protocol):
    """Hashes and verifies passwords."""

    def hash(self, password: str) -> str:
        """Return a secure, salted hash of ``password``."""
        ...

    def verify(self, password: str, password_hash: str) -> bool:
        """Return ``True`` iff ``password`` matches ``password_hash``."""
        ...
