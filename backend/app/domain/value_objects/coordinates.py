"""Geographic coordinates value object.

``Coordinates`` is a foundational domain type used by emergency events, location
history, and risk assessments. It enforces the invariant that a point on Earth
has a latitude in [-90, 90] and a longitude in [-180, 180] — so an invalid point
can never exist in the domain in the first place.

Pure Python, immutable, framework-free.
"""

from __future__ import annotations

from dataclasses import dataclass

_LAT_MIN, _LAT_MAX = -90.0, 90.0
_LNG_MIN, _LNG_MAX = -180.0, 180.0


@dataclass(frozen=True, slots=True)
class Coordinates:
    """An immutable latitude/longitude pair, validated on construction.

    Raises:
        ValueError: If latitude or longitude is outside its valid range.
    """

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not _LAT_MIN <= self.latitude <= _LAT_MAX:
            msg = f"latitude must be within [{_LAT_MIN}, {_LAT_MAX}], got {self.latitude}"
            raise ValueError(msg)
        if not _LNG_MIN <= self.longitude <= _LNG_MAX:
            msg = f"longitude must be within [{_LNG_MIN}, {_LNG_MAX}], got {self.longitude}"
            raise ValueError(msg)

    def as_tuple(self) -> tuple[float, float]:
        """Return ``(latitude, longitude)`` — convenient for serialization."""
        return (self.latitude, self.longitude)
