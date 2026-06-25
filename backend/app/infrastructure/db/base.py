"""SQLAlchemy declarative base.

All ORM models (added from Phase 2 onward) inherit from :class:`Base`. Keeping
the base in its own module avoids import cycles between models and the session
factory, and gives Alembic a single ``Base.metadata`` to autogenerate against.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all SafeAI ORM models.

    ORM models live in ``app.infrastructure.db.models`` and are intentionally
    separate from domain entities — the database schema is an infrastructure
    detail, mapped to/from the framework-free domain by repositories.
    """
