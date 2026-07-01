"""bcrypt implementation of the ``PasswordHasher`` port."""

from __future__ import annotations

from app.core.security import hash_password, verify_password


class BcryptPasswordHasher:
    """Adapts the ``app.core.security`` bcrypt helpers to the domain port."""

    def hash(self, password: str) -> str:
        return hash_password(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return verify_password(password, password_hash)
