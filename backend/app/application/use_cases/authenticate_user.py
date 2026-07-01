"""Authenticate-user use case.

Application rule: authentication succeeds only when the email exists and the
password verifies against the stored hash. Both failure modes raise the *same*
``InvalidCredentialsError`` so callers cannot enumerate accounts.

Token issuance is intentionally **not** here — it depends on configuration
(the signing secret) and belongs at the edge. This use case answers only "are
these credentials valid, and if so, who is the user?".
"""

from __future__ import annotations

from dataclasses import dataclass

from app.application.use_cases.register_user import normalize_email
from app.domain.entities.user import User
from app.domain.exceptions import InvalidCredentialsError
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.password_hasher import PasswordHasher


@dataclass(frozen=True)
class AuthenticateUserCommand:
    """Input to :class:`AuthenticateUserUseCase`."""

    email: str
    password: str


class AuthenticateUserUseCase:
    """Verify a user's credentials."""

    def __init__(self, users: UserRepository, hasher: PasswordHasher) -> None:
        self._users = users
        self._hasher = hasher

    def execute(self, command: AuthenticateUserCommand) -> User:
        """Return the authenticated user.

        Raises:
            InvalidCredentialsError: If the email is unknown or the password is
                wrong (indistinguishable by design).
        """
        user = self._users.get_by_email(normalize_email(command.email))
        if user is None or not self._hasher.verify(command.password, user.password_hash):
            raise InvalidCredentialsError
        return user
