"""Tests for the Database holder and the session dependency.

Verifies that the factory-owned database connects (ping) and that the
``get_session`` dependency yields a usable, auto-closed session.
"""

from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.core.config import Settings
from app.infrastructure.db.session import Database
from app.main import create_app


def test_database_ping_succeeds_for_reachable_db(test_settings: Settings) -> None:
    database = Database(test_settings)
    try:
        assert database.ping() is True
    finally:
        database.dispose()


def test_get_session_yields_usable_session(test_settings: Settings) -> None:
    app = create_app(test_settings)

    @app.get("/api/v1/_test/db")
    def _db(session: Session = Depends(get_session)) -> dict[str, int]:
        value = session.execute(text("SELECT 1")).scalar_one()
        return {"value": int(value)}

    assert _exercise(app) == {"value": 1}


def _exercise(app: FastAPI) -> dict[str, int]:
    with TestClient(app) as client:
        response = client.get("/api/v1/_test/db")
    assert response.status_code == 200
    result: dict[str, int] = response.json()
    return result
