"""create emergency contacts and events tables

Revision ID: 0002_create_emergency_tables
Revises: 0001_create_users
Create Date: 2026-06-25

Phase 3: the ``emergency_contacts`` and ``emergency_events`` tables. Portable
across SQLite (local/tests) and PostgreSQL (compose/prod). Coordinates are
NUMERIC(9,6); idempotency is scoped per user via a composite unique constraint.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_create_emergency_tables"
down_revision: str | None = "0001_create_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BigIntPk = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "emergency_contacts",
        sa.Column("id", _BigIntPk, autoincrement=True, nullable=False),
        sa.Column("user_id", _BigIntPk, nullable=False),
        sa.Column("contact_name", sa.String(length=120), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column("relationship", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "phone_number", name="uq_contact_user_phone"),
    )
    op.create_index("ix_emergency_contacts_user_id", "emergency_contacts", ["user_id"])

    op.create_table(
        "emergency_events",
        sa.Column("id", _BigIntPk, autoincrement=True, nullable=False),
        sa.Column("user_id", _BigIntPk, nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "idempotency_key", name="uq_event_user_idempotency"),
    )
    op.create_index("ix_emergency_events_user_id", "emergency_events", ["user_id"])
    op.create_index("ix_events_user_created", "emergency_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_events_user_created", table_name="emergency_events")
    op.drop_index("ix_emergency_events_user_id", table_name="emergency_events")
    op.drop_table("emergency_events")
    op.drop_index("ix_emergency_contacts_user_id", table_name="emergency_contacts")
    op.drop_table("emergency_contacts")
