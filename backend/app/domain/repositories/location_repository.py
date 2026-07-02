"""Location history repository interface (port).

History is an append-only, time-ordered track: reads are always "a user's most
recent positions" — which is exactly the shape the port exposes. This access
pattern is also what the future risk-feature builder (Phase 5) consumes.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.location_sample import LocationSample


class LocationRepository(Protocol):
    """Persistence operations for :class:`LocationSample`."""

    def add(self, sample: LocationSample) -> LocationSample:
        """Persist a new sample and return it with ``id``/``recorded_at`` set."""
        ...

    def list_for_user(self, user_id: int, *, limit: int, offset: int) -> list[LocationSample]:
        """Return a page of a user's samples, **newest first**."""
        ...

    def count_for_user(self, user_id: int) -> int:
        """Return the total number of a user's samples (for pagination meta)."""
        ...
