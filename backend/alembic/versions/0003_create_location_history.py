"""create location history table

Revision ID: 0003_create_location_history
Revises: 0002_create_emergency_tables
Create Date: 2026-07-02

Phase 4: the ``location_history`` table — append-only, per-user, time-indexed.
This is the fastest-growing and most privacy-sensitive table; it is designed to
adopt time-based range partitioning and a retention window on PostgreSQL as it
grows (docs/database-design.md §5).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_create_location_history"
down_revision: str | None = "0002_create_emergency_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BigIntPk = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def upgrade() -> None:
    op.create_table(
        "location_history",
        sa.Column("id", _BigIntPk, autoincrement=True, nullable=False),
        sa.Column("user_id", _BigIntPk, nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column(
            "timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_location_history_user_id", "location_history", ["user_id"])
    op.create_index("ix_location_user_recorded", "location_history", ["user_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_location_user_recorded", table_name="location_history")
    op.drop_index("ix_location_history_user_id", table_name="location_history")
    op.drop_table("location_history")
