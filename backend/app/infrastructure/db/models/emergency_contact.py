"""SQLAlchemy ORM model for the ``emergency_contacts`` table."""

from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.columns import pk_column, user_id_fk


class EmergencyContactModel(Base):
    """A user's emergency contact.

    A user cannot register the same phone number twice (unique per user).
    """

    __tablename__ = "emergency_contacts"
    __table_args__ = (UniqueConstraint("user_id", "phone_number", name="uq_contact_user_phone"),)

    id: Mapped[int] = pk_column()
    user_id: Mapped[int] = user_id_fk()
    contact_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_number: Mapped[str] = mapped_column(String(20), nullable=False)
    relationship: Mapped[str | None] = mapped_column(String(50), nullable=True)
