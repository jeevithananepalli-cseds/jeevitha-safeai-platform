"""Shared pytest fixtures.

Fixtures mirror the application's dependency-injection wiring so tests construct
the app the same way production does — via the factory — but with test-scoped
settings and an isolated, schema-created SQLite database per test.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.infrastructure.db.base import Base
from app.main import create_app

# Note: importing app.main transitively imports the ORM models (via the API
# router → deps → repository), registering every table on Base.metadata before
# the fixtures below call create_all().


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Settings for one test.

    Uses an isolated SQLite file by default (zero-dependency local runs). When
    ``SAFEAI_TEST_DATABASE_URL`` is set (CI points it at PostgreSQL), the suite
    runs against that instead — real-dialect fidelity, with the schema recreated
    per test by the ``app`` fixture.
    """
    db_url = (
        os.environ.get("SAFEAI_TEST_DATABASE_URL")
        or f"sqlite:///{(tmp_path / 'safeai_test.db').as_posix()}"
    )
    return Settings(
        environment="development",
        database_url=db_url,
        jwt_secret_key="test-secret-key-at-least-32-bytes-long!",
        access_token_expire_minutes=60,
        log_level="WARNING",
    )


@pytest.fixture
def app(test_settings: Settings) -> Iterator[FastAPI]:
    """A FastAPI app with a freshly created schema, torn down afterward."""
    application = create_app(test_settings)
    engine = application.state.database.engine
    Base.metadata.create_all(bind=engine)
    yield application
    Base.metadata.drop_all(bind=engine)
    application.state.database.dispose()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """A test client bound to the schema-created app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
    """Register + log in a user and return an Authorization header.

    Foundation for testing protected endpoints in later phases: any test that
    needs an authenticated request depends on this fixture.
    """
    credentials = {
        "name": "Fixture User",
        "email": "fixture-user@example.com",
        "password": "fixture-pass-123",
    }
    register = client.post("/api/v1/auth/register", json=credentials)
    assert register.status_code == 201, register.text
    login = client.post(
        "/api/v1/auth/login",
        json={"email": credentials["email"], "password": credentials["password"]},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
