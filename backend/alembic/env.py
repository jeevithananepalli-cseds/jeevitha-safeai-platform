"""Alembic migration environment.

Wires Alembic to the application's configuration and ORM metadata:

* the database URL comes from :class:`~app.core.config.Settings` (env-driven),
  never from ``alembic.ini`` — so no credentials live in version control;
* ``target_metadata`` is the shared declarative ``Base.metadata``, enabling
  ``alembic revision --autogenerate`` to diff models against the database.

Models are imported for their side effect of registering tables on
``Base.metadata``. From Phase 2 onward, importing ``app.infrastructure.db.models``
pulls in every model; today that package may be empty, which is fine.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Importing the models package registers all ORM tables on Base.metadata.
# (No-op while the package is empty in Phase 1.)
import app.infrastructure.db.models  # noqa: F401
from app.core.config import get_settings
from app.infrastructure.db.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject the runtime database URL from application settings.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without a DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live DB connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
