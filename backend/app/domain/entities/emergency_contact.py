"""Emergency contact domain entity.

A trusted person to be notified during an emergency. Plain, immutable Python;
the phone number is expected in E.164 form (validated at the API boundary).
``id`` is ``None`` until persisted.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EmergencyContact:
    """A user's emergency contact."""

    user_id: int
    contact_name: str
    phone_number: str
    relationship: str | None = None
    id: int | None = None
