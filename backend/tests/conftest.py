"""Shared pytest fixtures.

Fixtures mirror the application's dependency-injection wiring so tests construct
the app the same way production does — via the factory — but with test-scoped
settings. This is the foundation other phases build their fixtures on (DB
sessions, authenticated clients, factories).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Settings for the test environment.

    Uses an in-memory-style SQLite database and a fixed JWT secret so tests are
    deterministic and need no external services.
    """
    return Settings(
        environment="development",
        database_url="sqlite:///./test_safeai.db",
        jwt_secret_key="test-secret-not-used-in-production",
        log_level="WARNING",
    )


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    """A FastAPI test client built from the application factory."""
    app = create_app(test_settings)
    with TestClient(app) as test_client:
        yield test_client
