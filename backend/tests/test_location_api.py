"""End-to-end API tests for the location endpoints.

Full stack: routers → use cases → repository → database, plus JWT auth,
per-user isolation, ordering, and pagination per docs/api-contract.md.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

UPDATE_URL = "/api/v1/location/update"
HISTORY_URL = "/api/v1/location/history"


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": email, "password": "password123"},
    )
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


# --- record -------------------------------------------------------------------


def test_update_location_returns_201_with_sample(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        UPDATE_URL, json={"latitude": 17.385044, "longitude": 78.486671}, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"]
    assert data["latitude"] == 17.385044
    assert data["longitude"] == 78.486671
    assert data["timestamp"]


def test_update_location_requires_auth(client: TestClient) -> None:
    assert client.post(UPDATE_URL, json={"latitude": 0, "longitude": 0}).status_code == 401


def test_update_location_rejects_out_of_range_coordinates(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(UPDATE_URL, json={"latitude": 91, "longitude": 0}, headers=auth_headers)
    assert response.status_code == 422
    assert "latitude" in response.json()["error"]["details"]

    response = client.post(
        UPDATE_URL, json={"latitude": 0, "longitude": -181}, headers=auth_headers
    )
    assert response.status_code == 422
    assert "longitude" in response.json()["error"]["details"]


def test_update_location_rejects_missing_fields(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(UPDATE_URL, json={"latitude": 10}, headers=auth_headers)
    assert response.status_code == 422
    assert "longitude" in response.json()["error"]["details"]


# --- history ------------------------------------------------------------------


def test_history_returns_newest_first(client: TestClient, auth_headers: dict[str, str]) -> None:
    for lat in (1.0, 2.0, 3.0):  # recorded in this order
        client.post(UPDATE_URL, json={"latitude": lat, "longitude": 0}, headers=auth_headers)

    response = client.get(HISTORY_URL, headers=auth_headers)

    assert response.status_code == 200
    latitudes = [item["latitude"] for item in response.json()["data"]]
    assert latitudes == [3.0, 2.0, 1.0]


def test_history_pagination_meta_and_second_page(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    for lat in (1.0, 2.0, 3.0):
        client.post(UPDATE_URL, json={"latitude": lat, "longitude": 0}, headers=auth_headers)

    first = client.get(f"{HISTORY_URL}?page=1&limit=2", headers=auth_headers).json()
    assert first["meta"] == {"total": 3, "page": 1, "limit": 2}
    assert [i["latitude"] for i in first["data"]] == [3.0, 2.0]

    second = client.get(f"{HISTORY_URL}?page=2&limit=2", headers=auth_headers).json()
    assert second["meta"] == {"total": 3, "page": 2, "limit": 2}
    assert [i["latitude"] for i in second["data"]] == [1.0]


def test_history_requires_auth(client: TestClient) -> None:
    assert client.get(HISTORY_URL).status_code == 401


def test_history_is_isolated_per_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post(UPDATE_URL, json={"latitude": 5, "longitude": 5}, headers=auth_headers)

    other = _auth(client, "someone-else@example.com")
    response = client.get(HISTORY_URL, headers=other)

    assert response.json()["meta"]["total"] == 0
    assert response.json()["data"] == []


def test_history_empty_for_new_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.get(HISTORY_URL, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"] == []
    assert response.json()["meta"]["total"] == 0
