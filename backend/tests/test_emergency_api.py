"""End-to-end API tests for contacts and the emergency (SOS) workflow.

Exercises the full stack (routers → use cases → repositories → SQLite) plus JWT
auth, per-user isolation, and SOS idempotency.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

CONTACTS_URL = "/api/v1/contacts"
SOS_URL = "/api/v1/emergency/sos"


def _auth(client: TestClient, email: str) -> dict[str, str]:
    client.post(
        "/api/v1/auth/register",
        json={"name": "User", "email": email, "password": "password123"},
    )
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


# --- contacts -----------------------------------------------------------------


def test_add_contact_returns_201(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        CONTACTS_URL,
        json={"contact_name": "Amma", "phone_number": "+919876543210", "relationship": "parent"},
        headers=auth_headers,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"]
    assert data["phone_number"] == "+919876543210"


def test_add_contact_requires_auth(client: TestClient) -> None:
    response = client.post(
        CONTACTS_URL, json={"contact_name": "X", "phone_number": "+919876543210"}
    )
    assert response.status_code == 401


def test_add_contact_rejects_invalid_phone(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        CONTACTS_URL, json={"contact_name": "X", "phone_number": "12345"}, headers=auth_headers
    )
    assert response.status_code == 422
    assert "phone_number" in response.json()["error"]["details"]


def test_add_contact_rejects_duplicate(client: TestClient, auth_headers: dict[str, str]) -> None:
    payload = {"contact_name": "Amma", "phone_number": "+919876543210"}
    client.post(CONTACTS_URL, json=payload, headers=auth_headers)
    response = client.post(CONTACTS_URL, json=payload, headers=auth_headers)
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "duplicate_contact"


def test_list_contacts_is_paginated(client: TestClient, auth_headers: dict[str, str]) -> None:
    for i in range(3):
        client.post(
            CONTACTS_URL,
            json={"contact_name": f"C{i}", "phone_number": f"+91987654321{i}"},
            headers=auth_headers,
        )
    response = client.get(f"{CONTACTS_URL}?page=1&limit=2", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["meta"] == {"total": 3, "page": 1, "limit": 2}
    assert len(body["data"]) == 2


def test_contacts_are_isolated_per_user(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post(
        CONTACTS_URL,
        json={"contact_name": "Mine", "phone_number": "+919876543210"},
        headers=auth_headers,
    )
    other = _auth(client, "other@example.com")
    response = client.get(CONTACTS_URL, headers=other)
    assert response.json()["meta"]["total"] == 0


# --- SOS ----------------------------------------------------------------------


def test_sos_creates_active_event(client: TestClient, auth_headers: dict[str, str]) -> None:
    response = client.post(
        SOS_URL, json={"latitude": 17.385, "longitude": 78.486}, headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["status"] == "active"
    assert data["id"]
    assert data["notified_contacts"] == 0  # no contacts added


def test_sos_notifies_contacts(client: TestClient, auth_headers: dict[str, str]) -> None:
    client.post(
        CONTACTS_URL,
        json={"contact_name": "A", "phone_number": "+919876543210"},
        headers=auth_headers,
    )
    response = client.post(SOS_URL, json={"latitude": 0, "longitude": 0}, headers=auth_headers)
    assert response.json()["data"]["notified_contacts"] == 1


def test_sos_is_idempotent_with_key(client: TestClient, auth_headers: dict[str, str]) -> None:
    headers = {**auth_headers, "Idempotency-Key": "sos-key-123"}
    first = client.post(SOS_URL, json={"latitude": 1, "longitude": 2}, headers=headers)
    second = client.post(SOS_URL, json={"latitude": 1, "longitude": 2}, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 200  # idempotent replay
    assert first.json()["data"]["id"] == second.json()["data"]["id"]


def test_sos_requires_auth(client: TestClient) -> None:
    assert client.post(SOS_URL, json={"latitude": 0, "longitude": 0}).status_code == 401


def test_two_keyless_sos_create_distinct_events(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Without an Idempotency-Key, each SOS is a new event.
    first = client.post(SOS_URL, json={"latitude": 1, "longitude": 2}, headers=auth_headers)
    second = client.post(SOS_URL, json={"latitude": 1, "longitude": 2}, headers=auth_headers)
    assert first.json()["data"]["id"] != second.json()["data"]["id"]


def test_list_contacts_requires_auth(client: TestClient) -> None:
    assert client.get(CONTACTS_URL).status_code == 401


def test_sos_rejects_out_of_range_coordinates(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(SOS_URL, json={"latitude": 200, "longitude": 0}, headers=auth_headers)
    assert response.status_code == 422


# --- get event ----------------------------------------------------------------


def test_get_event_returns_owner_event(client: TestClient, auth_headers: dict[str, str]) -> None:
    created = client.post(
        SOS_URL, json={"latitude": 1, "longitude": 2}, headers=auth_headers
    ).json()["data"]
    response = client.get(f"/api/v1/emergency/{created['id']}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["data"]["id"] == created["id"]


def test_get_event_hides_other_users_event(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    created = client.post(
        SOS_URL, json={"latitude": 1, "longitude": 2}, headers=auth_headers
    ).json()["data"]
    other = _auth(client, "other2@example.com")
    response = client.get(f"/api/v1/emergency/{created['id']}", headers=other)
    assert response.status_code == 404  # not-owned looks like not-found


def test_get_event_unknown_returns_404_envelope(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.get("/api/v1/emergency/999999", headers=auth_headers)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_get_event_non_integer_id_returns_422(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    # Path param typed as int — a non-numeric id fails validation.
    assert client.get("/api/v1/emergency/not-a-number", headers=auth_headers).status_code == 422


# --- event status lifecycle -----------------------------------------------------


def _create_event(client: TestClient, headers: dict[str, str]) -> int:
    created = client.post(SOS_URL, json={"latitude": 1, "longitude": 2}, headers=headers)
    event_id: int = created.json()["data"]["id"]
    return event_id


def test_event_full_lifecycle_active_to_resolved(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    event_id = _create_event(client, auth_headers)

    ack = client.patch(
        f"/api/v1/emergency/{event_id}/status",
        json={"status": "acknowledged"},
        headers=auth_headers,
    )
    assert ack.status_code == 200
    assert ack.json()["data"]["status"] == "acknowledged"

    resolved = client.patch(
        f"/api/v1/emergency/{event_id}/status",
        json={"status": "resolved"},
        headers=auth_headers,
    )
    assert resolved.status_code == 200
    assert resolved.json()["data"]["status"] == "resolved"

    # The transition is durable: a fresh read sees the final state.
    fetched = client.get(f"/api/v1/emergency/{event_id}", headers=auth_headers)
    assert fetched.json()["data"]["status"] == "resolved"


def test_resolved_event_cannot_be_reopened(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    event_id = _create_event(client, auth_headers)
    client.patch(
        f"/api/v1/emergency/{event_id}/status", json={"status": "resolved"}, headers=auth_headers
    )

    response = client.patch(
        f"/api/v1/emergency/{event_id}/status",
        json={"status": "acknowledged"},
        headers=auth_headers,
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status_transition"


def test_update_status_rejects_unknown_status_value(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    event_id = _create_event(client, auth_headers)
    response = client.patch(
        f"/api/v1/emergency/{event_id}/status", json={"status": "panic"}, headers=auth_headers
    )
    assert response.status_code == 422


def test_update_status_hides_other_users_event(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    event_id = _create_event(client, auth_headers)
    other = _auth(client, "intruder@example.com")
    response = client.patch(
        f"/api/v1/emergency/{event_id}/status", json={"status": "cancelled"}, headers=other
    )
    assert response.status_code == 404


def test_update_status_requires_auth(client: TestClient) -> None:
    response = client.patch("/api/v1/emergency/1/status", json={"status": "resolved"})
    assert response.status_code == 401


def test_list_contacts_second_page(client: TestClient, auth_headers: dict[str, str]) -> None:
    for i in range(3):
        client.post(
            CONTACTS_URL,
            json={"contact_name": f"C{i}", "phone_number": f"+91987654321{i}"},
            headers=auth_headers,
        )
    response = client.get(f"{CONTACTS_URL}?page=2&limit=2", headers=auth_headers)
    body = response.json()
    assert body["meta"] == {"total": 3, "page": 2, "limit": 2}
    assert len(body["data"]) == 1  # the remaining contact
