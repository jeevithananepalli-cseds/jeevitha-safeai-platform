"""Application factory and ASGI entry point.

``create_app`` is an **application factory**: it constructs and configures a
FastAPI instance and returns it, rather than building a global app at import
time. This keeps wiring explicit and lets tests build an isolated app with their
own settings (see ``docs/glossary.md`` → *Application factory*).

The module also exposes ``app`` for ASGI servers (``uvicorn app.main:app``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.db.session import Database

logger = get_logger(__name__)

API_V1_PREFIX = "/api/v1"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional settings override (tests inject their own); defaults
            to the process-wide cached settings.

    Returns:
        A fully configured :class:`fastapi.FastAPI` instance.
    """
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    # Fail fast on insecure/missing configuration before serving any request.
    settings.validate_runtime()

    # Build the database for THIS app instance from the injected settings, so the
    # engine honors the same configuration as the rest of the app (no global).
    database = Database(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "Starting %s v%s (environment=%s)",
            settings.app_name,
            settings.version,
            settings.environment,
        )
        yield
        database.dispose()
        logger.info("Shutting down %s", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        summary="Intelligent Women's Safety & Emergency Response Platform",
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # Expose the configured settings and database to dependency providers
    # (app.api.deps) via application state — the composition-root handoff.
    app.state.settings = settings
    app.state.database = database

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=API_V1_PREFIX)

    return app


# ASGI application instance used by uvicorn / the Docker entrypoint.
app = create_app()
