"""Location sample domain entity.

A single recorded position of a user at a moment in time — the unit of the
location-history track. Location history is append-only (samples are recorded,
never edited), which is why the entity has no mutation behavior. It reuses the
framework-free :class:`Coordinates` value object so an invalid position can
never enter the domain.

``id`` and ``recorded_at`` are ``None`` until persisted.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from app.domain.value_objects.coordinates import Coordinates


@dataclass(frozen=True, slots=True)
class LocationSample:
    """One point of a user's location history."""

    user_id: int
    location: Coordinates
    id: int | None = None
    recorded_at: dt.datetime | None = None
