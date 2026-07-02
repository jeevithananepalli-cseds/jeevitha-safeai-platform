"""Record-location use case.

Appends one sample to the user's location history. Deliberately minimal: the
history is an append-only track (no dedupe, no mutation), and the coordinate
invariants are already guaranteed by the ``Coordinates`` value object the
command carries.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.entities.location_sample import LocationSample
from app.domain.repositories.location_repository import LocationRepository
from app.domain.value_objects.coordinates import Coordinates


@dataclass(frozen=True)
class RecordLocationCommand:
    """Input to :class:`RecordLocationUseCase`."""

    user_id: int
    location: Coordinates


class RecordLocationUseCase:
    """Append a position to the user's location history."""

    def __init__(self, locations: LocationRepository) -> None:
        self._locations = locations

    def execute(self, command: RecordLocationCommand) -> LocationSample:
        sample = LocationSample(user_id=command.user_id, location=command.location)
        return self._locations.add(sample)
