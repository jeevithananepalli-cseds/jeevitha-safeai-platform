"""Shared response schemas: the consistent API envelope.

Every endpoint returns the same shape — ``{ success, data, error, meta }`` — so
the frontend can handle responses uniformly. This mirrors the contract in
``docs/api-contract.md``. The envelope is generic over the payload type for full
type safety end-to-end. ``meta`` is ``null`` except on paginated list responses.
"""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Machine-readable error information returned on failure."""

    code: str
    message: str
    details: dict[str, str] = {}


class PageMeta(BaseModel):
    """Pagination metadata accompanying a paginated list response."""

    total: int
    page: int
    limit: int


class ApiResponse[T](BaseModel):
    """The standard success/error envelope wrapping every response.

    On success: ``success=True``, ``data`` is the payload, ``error`` is ``None``.
    On failure: ``success=False``, ``data`` is ``None``, ``error`` is populated.
    ``meta`` is populated only on paginated list responses.
    """

    success: bool
    data: T | None = None
    error: ErrorDetail | None = None
    meta: PageMeta | None = None

    @classmethod
    def ok(cls, data: T) -> ApiResponse[T]:
        """Build a success envelope around ``data``."""
        return cls(success=True, data=data, error=None)

    @classmethod
    def paginated(cls, data: T, *, total: int, page: int, limit: int) -> ApiResponse[T]:
        """Build a success envelope for a page of a list, with pagination meta."""
        return cls(
            success=True,
            data=data,
            error=None,
            meta=PageMeta(total=total, page=page, limit=limit),
        )

    @classmethod
    def fail(cls, code: str, message: str, details: dict[str, str] | None = None) -> ApiResponse[T]:
        """Build an error envelope."""
        return cls(
            success=False,
            data=None,
            error=ErrorDetail(code=code, message=message, details=details or {}),
        )
