"""Tests for the reusable pagination primitives.

Covers the ``Pagination`` params dependency, its query-parameter validation, and
the paginated response envelope — the foundation every list endpoint in Phases
3-5 will build on.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import PaginationDep
from app.api.pagination import Pagination
from app.api.v1.schemas.common import ApiResponse


def test_offset_is_derived_from_page_and_limit() -> None:
    assert Pagination(page=1, limit=20).offset == 0
    assert Pagination(page=3, limit=10).offset == 20


def test_paginated_envelope_carries_meta() -> None:
    response = ApiResponse.paginated([1, 2, 3], total=42, page=2, limit=3)
    assert response.success is True
    assert response.meta is not None
    assert response.meta.total == 42
    assert response.meta.page == 2
    assert response.meta.limit == 3


def _mount_list_route(app: FastAPI) -> None:
    @app.get("/api/v1/_test/items")
    def _items(pagination: PaginationDep) -> ApiResponse[list[int]]:
        items = list(range(pagination.offset, pagination.offset + pagination.limit))
        return ApiResponse.paginated(items, total=100, page=pagination.page, limit=pagination.limit)


def test_pagination_params_drive_response(app: FastAPI) -> None:
    _mount_list_route(app)
    with TestClient(app) as client:
        response = client.get("/api/v1/_test/items?page=2&limit=5")

    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {"total": 100, "page": 2, "limit": 5}
    assert body["data"] == [5, 6, 7, 8, 9]


def test_pagination_defaults_when_omitted(app: FastAPI) -> None:
    _mount_list_route(app)
    with TestClient(app) as client:
        body = client.get("/api/v1/_test/items").json()
    assert body["meta"] == {"total": 100, "page": 1, "limit": 20}


def test_pagination_rejects_out_of_range_values(app: FastAPI) -> None:
    _mount_list_route(app)
    with TestClient(app) as client:
        assert client.get("/api/v1/_test/items?page=0").status_code == 422
        assert client.get("/api/v1/_test/items?limit=1000").status_code == 422
