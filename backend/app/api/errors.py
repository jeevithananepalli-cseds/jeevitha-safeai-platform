"""Global exception handlers — enforce the API response envelope on every path.

Without these, FastAPI/Starlette emit their native error shapes (e.g.
``{"detail": ...}``) for validation and HTTP errors, breaking the
``{success, data, error}`` contract that the frontend client relies on. These
handlers convert *all* error responses — validation, HTTP, and unhandled — into
the standard envelope, and ensure internal detail is logged server-side and
never returned to clients (see docs/architecture.md §7).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.schemas.common import ApiResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

# Map HTTP status codes to stable, machine-readable error codes (api-contract.md).
_STATUS_TO_CODE: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
}


def _format_validation_errors(errors: Sequence[Any]) -> dict[str, str]:
    """Flatten pydantic validation errors into a ``field -> message`` map.

    The location prefix (``body``/``query``/``path``) is dropped so the key is
    the offending field name, matching the ``details`` shape in api-contract.md.
    """
    details: dict[str, str] = {}
    for error in errors:
        location = [
            str(part) for part in error.get("loc", ()) if part not in ("body", "query", "path")
        ]
        field = ".".join(location) or "__root__"
        details[field] = error.get("msg", "invalid value")
    return details


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return ``422`` with the envelope for request validation failures."""
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - defensive
        raise exc
    payload: ApiResponse[None] = ApiResponse.fail(
        "validation_error",
        "Request validation failed.",
        _format_validation_errors(exc.errors()),
    )
    return JSONResponse(status_code=422, content=payload.model_dump())


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return the envelope for explicitly raised HTTP errors (404, 409, ...)."""
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - defensive
        raise exc
    code = _STATUS_TO_CODE.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed."
    payload: ApiResponse[None] = ApiResponse.fail(code, message)
    headers = getattr(exc, "headers", None)
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump(), headers=headers)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all: log the real error, return a safe generic ``500`` envelope."""
    logger.exception("Unhandled error processing %s %s", request.method, request.url.path)
    payload: ApiResponse[None] = ApiResponse.fail(
        "internal_error",
        "An unexpected error occurred.",
    )
    return JSONResponse(status_code=500, content=payload.model_dump())


def register_exception_handlers(app: FastAPI) -> None:
    """Register all envelope-enforcing handlers on the application."""
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
