"""Application factory and ASGI entry point.

``create_app`` is an **application factory**: it constructs and configures a
FastAPI instance and returns it, rather than building a global app at import
time. This keeps wiring explicit and lets tests build an isolated app with their
own settings (see ``docs/glossary.md`` → *Application factory*).

The module also exposes ``app`` for ASGI servers (``uvicorn app.main:app``).
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, get_logger
from app.infrastructure.db.session import Database

logger = get_logger(__name__)

API_V1_PREFIX = "/api/v1"

# Requests slower than this are logged as warnings (observability groundwork).
SLOW_REQUEST_THRESHOLD_MS = 500.0


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
    # Compress larger JSON responses (paginated lists compress well); small
    # payloads are passed through untouched.
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def request_timing(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Attach per-request latency and surface slow requests.

        Every response carries ``X-Process-Time-Ms``; requests slower than
        ``SLOW_REQUEST_THRESHOLD_MS`` are logged as warnings so latency
        regressions are visible before users report them.
        """
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"
        if elapsed_ms > SLOW_REQUEST_THRESHOLD_MS:
            logger.warning(
                "Slow request: %s %s -> %s (%.1f ms)",
                request.method,
                request.url.path,
                response.status_code,
                elapsed_ms,
            )
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix=API_V1_PREFIX)

    return app


# ASGI application instance used by uvicorn / the Docker entrypoint.
app = create_app()
