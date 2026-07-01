"""Reusable pagination query parameters.

A single dependency shared by every list endpoint (contacts, location history,
recommendations — Phases 3-5) so pagination is validated and applied
consistently, and matches the ``meta`` contract in docs/api-contract.md.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

_DEFAULT_LIMIT = 20
_MAX_LIMIT = 100


@dataclass(frozen=True)
class Pagination:
    """A validated page request."""

    page: int
    limit: int

    @property
    def offset(self) -> int:
        """Zero-based row offset for the requested page."""
        return (self.page - 1) * self.limit


def pagination_params(
    page: int = Query(default=1, ge=1, description="1-based page number"),
    limit: int = Query(default=_DEFAULT_LIMIT, ge=1, le=_MAX_LIMIT, description="Items per page"),
) -> Pagination:
    """Provide validated pagination parameters from the query string."""
    return Pagination(page=page, limit=limit)
