"""API tests for the authentication and profile endpoints (end-to-end).

Runs against the schema-created SQLite app from conftest, exercising the full
stack: routers → use cases → repositories → database, plus JWT auth.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
PROFILE_URL = "/api/v1/profile"

VALID = {"name": "Jeevitha", "email": "jeevitha@example.com", "password": "a-good-password"}


def _register(client: TestClient, **overrides: str) -> None:
    payload = {**VALID, **overrides}
    response = client.post(REGISTER_URL, json=payload)
    assert response.status_code == 201, response.text


def _login_token(
    client: TestClient, email: str = VALID["email"], password: str = VALID["password"]
) -> str:
    response = client.post(LOGIN_URL, json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    token: str = response.json()["data"]["access_token"]
    return token


# --- register -----------------------------------------------------------------


def test_register_returns_201_and_never_exposes_password(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json=VALID)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"]
    assert data["email"] == "jeevitha@example.com"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_returns_409(client: TestClient) -> None:
    _register(client)
    response = client.post(REGISTER_URL, json={**VALID, "name": "Someone Else"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"


def test_register_weak_password_returns_422(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json={**VALID, "password": "short"})

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert "password" in body["error"]["details"]


def test_register_invalid_email_returns_422(client: TestClient) -> None:
    response = client.post(REGISTER_URL, json={**VALID, "email": "not-an-email"})
    assert response.status_code == 422
    assert "email" in response.json()["error"]["details"]


# --- login --------------------------------------------------------------------


def test_login_returns_bearer_token(client: TestClient) -> None:
    _register(client)
    response = client.post(LOGIN_URL, json={"email": VALID["email"], "password": VALID["password"]})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["access_token"]
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


def test_login_is_case_insensitive_on_email(client: TestClient) -> None:
    _register(client)
    response = client.post(
        LOGIN_URL, json={"email": "JEEVITHA@EXAMPLE.COM", "password": VALID["password"]}
    )
    assert response.status_code == 200


def test_login_wrong_password_returns_401(client: TestClient) -> None:
    _register(client)
    response = client.post(LOGIN_URL, json={"email": VALID["email"], "password": "wrong-password"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


def test_login_unknown_email_returns_401(client: TestClient) -> None:
    response = client.post(LOGIN_URL, json={"email": "nobody@example.com", "password": "whatever"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


# --- profile ------------------------------------------------------------------


def test_profile_requires_authentication(client: TestClient) -> None:
    response = client.get(PROFILE_URL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_profile_rejects_malformed_token(client: TestClient) -> None:
    response = client.get(PROFILE_URL, headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_full_flow_register_login_profile(client: TestClient) -> None:
    _register(client)
    token = _login_token(client)

    response = client.get(PROFILE_URL, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == VALID["email"]
    assert data["name"] == VALID["name"]


def test_profile_via_auth_headers_fixture(client: TestClient, auth_headers: dict[str, str]) -> None:
    # Exercises the shared `auth_headers` fixture that later phases reuse.
    response = client.get(PROFILE_URL, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "fixture-user@example.com"
