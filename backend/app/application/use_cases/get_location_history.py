"""Get-location-history use case (paginated, newest first).

Reads only the requesting user's samples — per-user isolation is structural
because the repository is always queried by ``user_id``.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.location_sample import LocationSample
from app.domain.repositories.location_repository import LocationRepository


@dataclass(frozen=True)
class LocationHistoryPage:
    """A page of samples plus the total count (for pagination metadata)."""

    items: list[LocationSample]
    total: int


class GetLocationHistoryUseCase:
    """Return a page of the user's location history, most recent first."""

    def __init__(self, locations: LocationRepository) -> None:
        self._locations = locations

    def execute(self, user_id: int, *, limit: int, offset: int) -> LocationHistoryPage:
        items = self._locations.list_for_user(user_id, limit=limit, offset=offset)
        total = self._locations.count_for_user(user_id)
        return LocationHistoryPage(items=items, total=total)
