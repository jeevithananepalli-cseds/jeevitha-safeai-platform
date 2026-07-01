"""User domain entity.

A ``User`` is a person with an account. The entity is plain, immutable Python —
it holds the stored password *hash* (never a plaintext password) and knows
nothing about SQLAlchemy or HTTP. Persistence maps this entity to/from an ORM
model in the infrastructure layer.

``id`` and ``created_at`` are ``None`` for a not-yet-persisted user; the
repository returns a copy with both populated after insertion.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class User:
    """An account holder.

    Attributes:
        name: Display name.
        email: Normalized (lowercased) unique login identifier.
        password_hash: bcrypt hash of the user's password — never plaintext.
        id: Surrogate key, or ``None`` before persistence.
        created_at: Creation timestamp (UTC), or ``None`` before persistence.
    """

    name: str
    email: str
    password_hash: str
    id: int | None = None
    created_at: dt.datetime | None = None
