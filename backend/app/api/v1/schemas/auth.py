"""Request/response schemas for authentication and user endpoints.

These DTOs define and validate the wire contract at the API boundary
(see docs/api-contract.md). They are distinct from the domain ``User`` entity —
notably, no schema ever exposes ``password_hash``.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.domain.entities.user import User

# bcrypt hashes at most the first 72 bytes; cap the password length accordingly
# and require a reasonable minimum.
_PASSWORD_MIN = 8
_PASSWORD_MAX = 72


def _validate_password_bytes(value: str) -> str:
    """Reject passwords over bcrypt's 72-*byte* limit.

    ``max_length`` counts characters; a multibyte password (e.g. emoji) can be
    within the character limit yet exceed 72 bytes, which bcrypt cannot hash.
    Validating here returns a clean 422 instead of a 500 at hashing time.
    """
    if len(value.encode("utf-8")) > _PASSWORD_MAX:
        msg = f"password must not exceed {_PASSWORD_MAX} bytes"
        raise ValueError(msg)
    return value


class RegisterRequest(BaseModel):
    """Body of ``POST /auth/register``."""

    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=_PASSWORD_MIN, max_length=_PASSWORD_MAX)

    _check_password_bytes = field_validator("password")(_validate_password_bytes)


class LoginRequest(BaseModel):
    """Body of ``POST /auth/login``."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=_PASSWORD_MAX)


class UserResponse(BaseModel):
    """Public representation of a user (never includes the password hash)."""

    id: int
    name: str
    email: EmailStr
    created_at: dt.datetime

    @classmethod
    def from_entity(cls, user: User) -> UserResponse:
        """Build a response DTO from a domain ``User`` (must be persisted)."""
        if user.id is None or user.created_at is None:
            msg = "cannot serialize an unpersisted user"
            raise ValueError(msg)
        return cls(
            id=user.id,
            name=user.name,
            email=user.email,
            created_at=user.created_at,
        )


class TokenResponse(BaseModel):
    """Access-token payload returned by ``POST /auth/login``."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
