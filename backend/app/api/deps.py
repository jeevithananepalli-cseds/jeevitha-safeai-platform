"""FastAPI dependency providers — the composition root.

These functions resolve per-request dependencies (settings, database, session)
from objects the application factory placed on ``app.state``. Keeping the wiring
here (the outer ``api`` layer) means inner layers never reach for globals, and
tests can override any provider via ``app.dependency_overrides``.
"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.infrastructure.db.session import Database


def get_app_settings(request: Request) -> Settings:
    """Return the settings the running app was configured with."""
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    """Return the app's :class:`Database` (engine + session factory)."""
    database: Database = request.app.state.database
    return database


def get_session(database: Database = Depends(get_database)) -> Iterator[Session]:
    """Yield a database session, guaranteeing it is closed afterward.

    The session is the only handle repositories receive; transaction control
    lives in the use cases that own the unit of work (from Phase 2).
    """
    with database.session_factory() as session:
        yield session
