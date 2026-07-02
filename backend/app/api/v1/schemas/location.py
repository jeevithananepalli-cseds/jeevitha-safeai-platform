"""Request/response schemas for location endpoints.

Coordinate ranges are validated at this boundary (and re-validated by the
``Coordinates`` value object in the domain — defense in depth).
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.domain.entities.location_sample import LocationSample


class LocationUpdateRequest(BaseModel):
    """Body of ``POST /location/update``."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LocationSampleResponse(BaseModel):
    """A returned location sample."""

    id: int
    latitude: float
    longitude: float
    timestamp: dt.datetime

    @classmethod
    def from_entity(cls, sample: LocationSample) -> LocationSampleResponse:
        if sample.id is None or sample.recorded_at is None:
            msg = "cannot serialize an unpersisted location sample"
            raise ValueError(msg)
        return cls(
            id=sample.id,
            latitude=sample.location.latitude,
            longitude=sample.location.longitude,
            timestamp=sample.recorded_at,
        )
