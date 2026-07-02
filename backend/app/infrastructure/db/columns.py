"""Reusable ORM column definitions shared across models.

Centralizing these keeps every table consistent and encodes hard-won details in
one place — notably the primary-key type, which must be ``BIGINT`` on PostgreSQL
but ``INTEGER`` on SQLite (only an ``INTEGER PRIMARY KEY`` auto-increments there).
Future models (emergency events, locations, risk assessments) reuse these so the
detail is never re-derived — or forgotten.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

# BIGINT on PostgreSQL, INTEGER on SQLite (portable auto-increment primary key).
BigIntPrimaryKey = BigInteger().with_variant(Integer, "sqlite")


def utcnow() -> dt.datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return dt.datetime.now(tz=dt.UTC)


def pk_column() -> Mapped[int]:
    """A surrogate big-integer primary key that auto-increments on any backend."""
    return mapped_column(BigIntPrimaryKey, primary_key=True, autoincrement=True)


def user_id_fk() -> Mapped[int]:
    """A required ``user_id`` foreign key to ``users.id``, indexed, cascading.

    The column type matches the users primary key. ``ON DELETE CASCADE`` removes
    a user's owned rows (contacts, events, ...) with the user — the privacy
    default for personal data.
    """
    return mapped_column(
        BigIntPrimaryKey,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def created_at_column() -> Mapped[dt.datetime]:
    """A ``created_at`` timestamp, set at insert time (UTC), never null.

    Uses a Python-side default so the value is available immediately after flush
    (no round-trip), plus a DB ``server_default`` as a backstop for inserts that
    bypass the ORM.
    """
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )


def updated_at_column() -> Mapped[dt.datetime]:
    """An ``updated_at`` timestamp, refreshed on every update (UTC), never null.

    For tables whose rows mutate in place (e.g. an emergency event's status
    lifecycle). ``onupdate`` refreshes it on ORM updates so the value always
    reflects the last change.
    """
    return mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
    )
