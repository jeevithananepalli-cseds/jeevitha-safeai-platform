"""Register-user use case.

Application rule: a new account requires a unique email and a securely hashed
password. This orchestrates the domain (``User``), the ``UserRepository`` port,
and the ``PasswordHasher`` port — with no framework or database code. It is fully
unit-testable with in-memory fakes.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.user import User
from app.domain.exceptions import EmailAlreadyExistsError
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.password_hasher import PasswordHasher


def normalize_email(email: str) -> str:
    """Normalize an email for storage and comparison (case-insensitive)."""
    return email.strip().lower()


@dataclass(frozen=True)
class RegisterUserCommand:
    """Input to :class:`RegisterUserUseCase`."""

    name: str
    email: str
    password: str


class RegisterUserUseCase:
    """Create a new user account."""

    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    def execute(self, command: RegisterUserCommand) -> User:
        """Register a user.

        Raises:
            EmailAlreadyExistsError: If the email is already registered.
        """
        email = normalize_email(command.email)
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyExistsError(email)

        user = User(
            name=command.name.strip(),
            email=email,
            password_hash=self._hasher.hash(command.password),
        )
        return self._users.add(user)
