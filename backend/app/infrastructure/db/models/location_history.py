"""SQLAlchemy ORM model for the ``location_history`` table.

The fastest-growing, most privacy-sensitive table in the system (see
docs/database-design.md §2.4 and §5): append-only, indexed for the one real read
pattern ("a user's recent track"), and designed to move to time-based range
partitioning with a retention window as it grows.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Index, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.columns import pk_column, user_id_fk, utcnow

# Same coordinate storage as emergency events: ~0.1 m precision, Python floats.
_Coordinate = Numeric(9, 6, asdecimal=False)


class LocationHistoryModel(Base):
    """One recorded position of a user."""

    __tablename__ = "location_history"
    __table_args__ = (
        # A user's recent track, newest-first — the hot read for history and
        # for risk-feature building (Phase 5).
        Index("ix_location_user_recorded", "user_id", "timestamp"),
    )

    id: Mapped[int] = pk_column()
    user_id: Mapped[int] = user_id_fk()
    latitude: Mapped[float] = mapped_column(_Coordinate, nullable=False)
    longitude: Mapped[float] = mapped_column(_Coordinate, nullable=False)
    # Column named `timestamp` per the database design; exposed to Python as
    # `recorded_at` for clarity.
    recorded_at: Mapped[dt.datetime] = mapped_column(
        "timestamp",
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
