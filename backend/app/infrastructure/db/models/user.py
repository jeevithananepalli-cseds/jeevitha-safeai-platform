"""SQLAlchemy ORM model for the ``users`` table.

This is an **infrastructure** detail — a mapping of the domain ``User`` to a
relational row. It is deliberately separate from the domain entity so the schema
can evolve independently; the repository translates between the two.

Email is stored lowercased (normalized by the application) with a unique index,
which keeps logins case-insensitive portably across SQLite and PostgreSQL
without relying on a Postgres-only ``CITEXT`` column.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base
from app.infrastructure.db.columns import created_at_column, pk_column


class UserModel(Base):
    """ORM mapping for a registered user."""

    __tablename__ = "users"

    id: Mapped[int] = pk_column()
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[dt.datetime] = created_at_column()
