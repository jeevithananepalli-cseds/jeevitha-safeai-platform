"""Tests that global exception handlers enforce the API envelope on error paths.

Feature endpoints arrive in later phases, so this module attaches a few
throwaway routes to a real app instance to exercise each handler: validation
(422), explicit HTTP errors (409/404), and unhandled exceptions (500).
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.config import Settings
from app.main import create_app


class _Body(BaseModel):
    name: str
    age: int


@pytest.fixture
def app_with_test_routes(test_settings: Settings) -> FastAPI:
    app = create_app(test_settings)

    @app.post("/api/v1/_test/echo")
    def _echo(body: _Body) -> dict[str, bool]:
        return {"ok": True}

    @app.get("/api/v1/_test/conflict")
    def _conflict() -> None:
        raise HTTPException(status_code=409, detail="That resource already exists.")

    @app.get("/api/v1/_test/crash")
    def _crash() -> None:
        raise ValueError("internal detail that must not leak")

    return app


def test_validation_error_uses_envelope(app_with_test_routes: FastAPI) -> None:
    client = TestClient(app_with_test_routes)
    # `age` is missing and the wrong type — should produce a 422 envelope.
    response = client.post("/api/v1/_test/echo", json={"name": "x", "age": "notanumber"})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "validation_error"
    assert "age" in body["error"]["details"]


def test_http_exception_uses_envelope(app_with_test_routes: FastAPI) -> None:
    client = TestClient(app_with_test_routes)
    response = client.get("/api/v1/_test/conflict")

    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "conflict"
    assert body["error"]["message"] == "That resource already exists."


def test_unknown_route_returns_not_found_envelope(app_with_test_routes: FastAPI) -> None:
    client = TestClient(app_with_test_routes)
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_unhandled_exception_returns_safe_500_envelope(app_with_test_routes: FastAPI) -> None:
    # raise_server_exceptions=False so the client returns the handler's response
    # instead of re-raising, mirroring real server behavior.
    client = TestClient(app_with_test_routes, raise_server_exceptions=False)
    response = client.get("/api/v1/_test/crash")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "internal_error"
    # The internal exception detail must never reach the client.
    assert "internal detail" not in response.text
