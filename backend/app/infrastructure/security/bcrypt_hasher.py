"""bcrypt implementation of the ``PasswordHasher`` port."""

from __future__ import annotations

from app.core.security import DEFAULT_BCRYPT_ROUNDS, hash_password, verify_password


class BcryptPasswordHasher:
    """Adapts the ``app.core.security`` bcrypt helpers to the domain port.

    The work factor comes from configuration (see ``Settings.bcrypt_rounds``);
    verification is cost-agnostic because bcrypt embeds the cost in each hash.
    """

    def __init__(self, rounds: int = DEFAULT_BCRYPT_ROUNDS) -> None:
        self._rounds = rounds

    def hash(self, password: str) -> str:
        return hash_password(password, rounds=self._rounds)

    def verify(self, password: str, password_hash: str) -> bool:
        return verify_password(password, password_hash)
