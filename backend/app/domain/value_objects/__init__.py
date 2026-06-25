"""Domain value objects — small immutable types defined by their value.

Value objects carry validation and meaning (e.g. valid geographic coordinates)
without identity. They are pure Python and safe to use across every layer.
"""

from app.domain.value_objects.coordinates import Coordinates

__all__ = ["Coordinates"]
