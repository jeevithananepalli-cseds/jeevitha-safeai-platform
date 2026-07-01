"""Settings-bound JWT token service.

Binds the pure ``app.core.security`` JWT helpers to the application's
configuration (signing secret, algorithm, expiry) so callers — the login route
and the current-user dependency — issue and decode tokens without ever handling
the secret themselves.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings
from app.core.security import TokenData, create_access_token, decode_access_token


@dataclass(frozen=True)
class IssuedToken:
    """A freshly issued access token and its lifetime in seconds."""

    access_token: str
    expires_in: int


class JwtTokenService:
    """Issues and decodes JWT access tokens using application settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def issue(self, subject: str) -> IssuedToken:
        """Issue an access token for ``subject`` (typically the user id)."""
        token = create_access_token(
            subject,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
            expires_minutes=self._settings.access_token_expire_minutes,
        )
        return IssuedToken(
            access_token=token,
            expires_in=self._settings.access_token_expire_minutes * 60,
        )

    def decode(self, token: str) -> TokenData:
        """Decode and validate a token, returning its claims."""
        return decode_access_token(
            token,
            self._settings.jwt_secret_key,
            algorithm=self._settings.jwt_algorithm,
        )
