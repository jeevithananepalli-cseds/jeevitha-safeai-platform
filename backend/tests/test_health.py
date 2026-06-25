"""API tests for the liveness and readiness endpoints.

Covers both the healthy and the database-down paths, and verifies the standard
envelope is used consistently (success/error semantics match the status code).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_database
from app.core.config import Settings
from app.main import create_app


class _FakeDatabase:
    """Stand-in Database whose readiness can be forced up or down in tests."""

    def __init__(self, *, healthy: bool) -> None:
        self._healthy = healthy

    def ping(self) -> bool:
        return self._healthy


# --- liveness -----------------------------------------------------------------


def test_liveness_is_alive(client: TestClient) -> None:
    response = client.get("/api/v1/health/live")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["error"] is None
    assert body["data"]["status"] == "alive"
    assert body["data"]["version"]
    # Liveness must not report on dependencies.
    assert "database" not in body["data"]


# --- readiness (healthy) ------------------------------------------------------


def test_readiness_is_ready_when_db_up(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ready"
    assert body["data"]["database"] == "up"


def test_health_alias_matches_readiness(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ready"


# --- readiness (degraded) -----------------------------------------------------


@pytest.fixture
def client_with_db_down(test_settings: Settings) -> Iterator[TestClient]:
    """A client whose database dependency reports as unreachable."""
    app = create_app(test_settings)
    app.dependency_overrides[get_database] = lambda: _FakeDatabase(healthy=False)
    with TestClient(app) as test_client:
        yield test_client


def test_readiness_returns_503_and_success_false_when_db_down(
    client_with_db_down: TestClient,
) -> None:
    response = client_with_db_down.get("/api/v1/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["success"] is False
    assert body["data"] is None
    assert body["error"]["code"] == "service_unavailable"
    assert body["error"]["details"]["database"] == "down"


def test_openapi_schema_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["info"]["title"]
