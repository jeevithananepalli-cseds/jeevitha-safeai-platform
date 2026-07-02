"""Database engine and session lifecycle.

Defines :class:`Database`, which owns the SQLAlchemy ``Engine`` and
``sessionmaker`` for **one application instance**. The application factory
(:func:`app.main.create_app`) builds a ``Database`` from the injected settings
and stores it on ``app.state`` — so the engine honors the same settings the rest
of the app was configured with (no import-time global). Tests can therefore
point an app at an isolated database purely through the factory.

The FastAPI dependency wiring (resolving ``Database``/``Session`` from the
request) lives at the composition root in ``app.api.deps`` to keep this module
free of framework imports.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _enable_sqlite_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    """Turn on SQLite foreign-key enforcement for each new connection.

    SQLite ignores foreign keys unless ``PRAGMA foreign_keys=ON`` is set per
    connection. Enabling it makes our ``ON DELETE CASCADE`` and FK constraints
    behave as they do on PostgreSQL — so tests catch violations that would
    otherwise slip through only to fail in production.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(settings: Settings) -> Engine:
    """Create a SQLAlchemy engine configured for the target database.

    SQLite needs ``check_same_thread=False`` because FastAPI may use the
    connection across threadpool workers. PostgreSQL uses a pooled connection
    with ``pool_pre_ping`` to transparently recover from dropped connections.
    """
    url = settings.database_url
    if url.startswith("sqlite"):
        engine = create_engine(url, connect_args={"check_same_thread": False}, future=True)
        event.listen(engine, "connect", _enable_sqlite_foreign_keys)
        return engine
    return create_engine(url, pool_pre_ping=True, future=True)


class Database:
    """Owns the engine and session factory for a single application instance.

    Constructed by the application factory from the active settings and stored on
    ``app.state.database``. Encapsulating these here (rather than as module
    globals) is what makes the database honor the factory's injected settings.
    """

    def __init__(self, settings: Settings) -> None:
        self.engine: Engine = create_db_engine(settings)
        self.session_factory: sessionmaker[Session] = sessionmaker(
            bind=self.engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )

    def ping(self) -> bool:
        """Return ``True`` if the database answers a trivial query.

        Used by the readiness probe. Failures are logged and reported as
        ``False`` rather than raised, so the endpoint can degrade gracefully.
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as exc:
            logger.warning("Database connectivity check failed: %s", exc)
            return False

    def dispose(self) -> None:
        """Release pooled connections. Called on application shutdown."""
        self.engine.dispose()
