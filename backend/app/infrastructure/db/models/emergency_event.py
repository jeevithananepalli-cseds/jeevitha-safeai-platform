"""SQLAlchemy ORM model for the ``emergency_events`` table."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.columns import (
    created_at_column,
    pk_column,
    updated_at_column,
    user_id_fk,
)

# Coordinates stored to ~0.1 m precision. asdecimal=False maps to Python float,
# matching the domain's Coordinates value object without Decimal conversions.
_Coordinate = Numeric(9, 6, asdecimal=False)


class EmergencyEventModel(Base):
    """A durable emergency event (e.g. an SOS)."""

    __tablename__ = "emergency_events"
    __table_args__ = (
        # Idempotency is scoped per user: a client key de-dupes that user's SOS.
        UniqueConstraint("user_id", "idempotency_key", name="uq_event_user_idempotency"),
        # A user's events, most-recent-first (the common read pattern).
        Index("ix_events_user_created", "user_id", "created_at"),
    )

    id: Mapped[int] = pk_column()
    user_id: Mapped[int] = user_id_fk()
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    latitude: Mapped[float] = mapped_column(_Coordinate, nullable=False)
    longitude: Mapped[float] = mapped_column(_Coordinate, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    idempotency_key: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[dt.datetime] = created_at_column()
    updated_at: Mapped[dt.datetime] = updated_at_column()
