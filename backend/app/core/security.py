"""Security utilities: password hashing and JWT access tokens.

These are pure, dependency-injected helpers used by the authentication use cases
(Phase 2). They live in ``core`` because they are cross-cutting infrastructure,
not business rules.

Choices (see docs/technology-decisions.md and architecture.md §7):

* **bcrypt** for password hashing — adaptive, salted, industry standard. We use
  the ``bcrypt`` library directly to avoid deprecation noise from wrappers.
* **PyJWT** for signed access tokens (HS256). The signing key comes from
  configuration (environment), never from source.

Nothing here logs or returns plaintext passwords or raw secrets.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import bcrypt
import jwt

# bcrypt operates on the first 72 bytes of a password. We surface this as an
# explicit guard rather than relying on silent truncation.
_BCRYPT_MAX_BYTES = 72


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired, or has a bad signature."""


@dataclass(frozen=True)
class TokenData:
    """Decoded, validated token claims relevant to the application."""

    subject: str
    expires_at: dt.datetime


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        password: The user's plaintext password.

    Returns:
        A bcrypt hash string safe to store in the database.

    Raises:
        ValueError: If the password exceeds bcrypt's 72-byte limit.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > _BCRYPT_MAX_BYTES:
        msg = f"password must not exceed {_BCRYPT_MAX_BYTES} bytes"
        raise ValueError(msg)
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Returns ``False`` (never raises) on any malformed input, so callers get a
    uniform negative result and avoid leaking *why* a check failed.
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str,
    secret_key: str,
    *,
    algorithm: str = "HS256",
    expires_minutes: int = 60,
    now: dt.datetime | None = None,
) -> str:
    """Create a signed JWT access token.

    Args:
        subject: The token subject (e.g. the user id), stored in the ``sub`` claim.
        secret_key: Signing key (from configuration).
        algorithm: JWT signing algorithm.
        expires_minutes: Token lifetime in minutes.
        now: Injectable current time (UTC) for deterministic tests.

    Returns:
        The encoded JWT string.
    """
    issued_at = now or dt.datetime.now(tz=dt.UTC)
    expires_at = issued_at + dt.timedelta(minutes=expires_minutes)
    payload = {
        "sub": subject,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_access_token(
    token: str,
    secret_key: str,
    *,
    algorithm: str = "HS256",
) -> TokenData:
    """Decode and validate a JWT access token.

    Args:
        token: The encoded JWT.
        secret_key: Signing key used to verify the signature.
        algorithm: Expected signing algorithm.

    Returns:
        The validated :class:`TokenData`.

    Raises:
        InvalidTokenError: If the token is expired, malformed, has a bad
            signature, or is missing required claims.
    """
    try:
        payload = jwt.decode(token, secret_key, algorithms=[algorithm])
    except jwt.PyJWTError as exc:
        raise InvalidTokenError(str(exc)) from exc

    subject = payload.get("sub")
    exp = payload.get("exp")
    if not isinstance(subject, str) or not isinstance(exp, int):
        raise InvalidTokenError("token is missing required claims")

    return TokenData(
        subject=subject,
        expires_at=dt.datetime.fromtimestamp(exp, tz=dt.UTC),
    )
