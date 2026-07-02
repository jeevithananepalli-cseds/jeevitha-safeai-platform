# API Contract — SafeAI v1

Base URL: `/api/v1`
Content type: `application/json` (UTF-8)
Auth: **Bearer JWT** in `Authorization: Bearer <token>` (except register/login/health).

This contract is the agreement between the Next.js frontend and the FastAPI
backend. It defines request/response shapes, status codes, and error handling.
The live, always-accurate schema is also served at `/docs` (Swagger) and
`/openapi.json`, generated from the pydantic models — this file is the
human-readable companion and source of intent.

---

## Conventions

### Response envelope

All responses use a consistent envelope:

```jsonc
// success
{ "success": true,  "data": { /* payload */ }, "error": null, "meta": null }

// error
{ "success": false, "data": null, "error": { "code": "string", "message": "human readable", "details": { } }, "meta": null }
```

`meta` is always present and is `null` except on paginated list responses, where
it carries pagination info:

```jsonc
{ "success": true, "data": [ /* items */ ], "error": null,
  "meta": { "total": 123, "page": 1, "limit": 20 } }
```

List endpoints accept `?page=<n>&limit=<m>` (`page` ≥ 1, `1` ≤ `limit` ≤ `100`,
defaults `page=1`, `limit=20`); out-of-range values return `422`.

### Status codes

| Code | Meaning | Used when |
|------|---------|-----------|
| `200 OK` | Success | Reads, successful actions returning existing data |
| `201 Created` | Resource created | Register, create contact, create SOS event |
| `400 Bad Request` | Validation error | Malformed/invalid input |
| `401 Unauthorized` | Missing/invalid token | Auth required and absent/expired |
| `403 Forbidden` | Authn ok, not allowed | Accessing another user's resource |
| `404 Not Found` | No such resource | Unknown id |
| `409 Conflict` | State conflict | Duplicate email, duplicate contact |
| `422 Unprocessable` | Schema validation | FastAPI/pydantic field errors |
| `429 Too Many Requests` | Rate limited | Login / SOS abuse protection |
| `500 Internal` | Server error | Unexpected; message is generic, detail logged |

### Error codes (stable, machine-readable)

`validation_error`, `invalid_credentials`, `unauthorized`, `forbidden`,
`not_found`, `conflict`, `email_taken`, `duplicate_contact`, `rate_limited`,
`service_unavailable`, `internal_error`.

> **Envelope enforced everywhere.** Global exception handlers convert *all*
> error responses — request validation (`422`), raised HTTP errors, and
> unhandled exceptions (`500`) — into this envelope. Internal exception detail is
> logged server-side and never returned to clients. So a client can rely on the
> `{ success, data, error }` shape on every response, success or failure.

---

## Health

Liveness and readiness are **separate** probes (see architecture.md §9):
liveness answers "is the process up?" with no dependency checks, while readiness
answers "can it do useful work?" by verifying the database. The container
healthcheck targets liveness; a load balancer targets readiness.

### `GET /api/v1/health/live`

Liveness probe — no dependencies. **No auth.** Always `200` while serving.

**200**
```json
{ "success": true, "data": { "status": "alive", "version": "0.1.0" }, "error": null }
```

### `GET /api/v1/health/ready`

Readiness probe — checks database connectivity. **No auth.**

**200** — ready
```json
{ "success": true, "data": { "status": "ready", "version": "0.1.0", "database": "up" }, "error": null }
```

**503** — not ready (database unreachable). Note `success` is `false`, consistent
with the status code:
```json
{ "success": false, "data": null,
  "error": { "code": "service_unavailable", "message": "Database is not reachable.",
             "details": { "database": "down" } } }
```

> `GET /api/v1/health` is retained as a backward-compatible alias of the
> readiness probe.

---

## Authentication

### `POST /api/v1/auth/register`

Create a new account. **No auth.**

**Request**
```json
{ "name": "Jeevitha N", "email": "jeevitha@example.com", "password": "S0me-Strong-Pass" }
```

**201**
```json
{ "success": true,
  "data": { "id": 1, "name": "Jeevitha N", "email": "jeevitha@example.com", "created_at": "2026-06-25T10:00:00Z" },
  "error": null }
```

**409** — email already registered
```json
{ "success": false, "data": null,
  "error": { "code": "email_taken", "message": "An account with this email already exists.", "details": {} } }
```

**422** — invalid input (e.g. weak/short password, bad email)
```json
{ "success": false, "data": null,
  "error": { "code": "validation_error", "message": "Invalid request.",
             "details": { "password": "must be at least 8 characters" } } }
```

> The password is hashed (bcrypt) server-side. The hash is never returned.

### `POST /api/v1/auth/login`

Exchange credentials for a JWT access token. **No auth.** Rate-limited.

**Request**
```json
{ "email": "jeevitha@example.com", "password": "S0me-Strong-Pass" }
```

**200**
```json
{ "success": true,
  "data": { "access_token": "<jwt>", "token_type": "bearer", "expires_in": 3600 },
  "error": null }
```

**401** — wrong email or password (identical message to avoid user enumeration)
```json
{ "success": false, "data": null,
  "error": { "code": "invalid_credentials", "message": "Invalid email or password.", "details": {} } }
```

---

## Users

### `GET /api/v1/profile`

Return the authenticated user's profile. **Auth required.**

**200**
```json
{ "success": true,
  "data": { "id": 1, "name": "Jeevitha N", "email": "jeevitha@example.com", "created_at": "2026-06-25T10:00:00Z" },
  "error": null }
```

**401** — missing/expired token.

---

## Emergency

### `POST /api/v1/emergency/sos`

Activate an SOS. **Auth required.** **Idempotent** via `Idempotency-Key` header.

**Headers**
```
Authorization: Bearer <jwt>
Idempotency-Key: 6f1c...   # client-generated; a retry with the same key returns the same event
```

**Request**
```json
{ "event_type": "sos", "latitude": 17.385044, "longitude": 78.486671 }
```

**201**
```json
{ "success": true,
  "data": { "id": 42, "event_type": "sos", "status": "active",
            "latitude": 17.385044, "longitude": 78.486671,
            "notified_contacts": 3, "created_at": "2026-06-25T10:05:00Z" },
  "error": null }
```

**200** — idempotent replay (same `Idempotency-Key`): returns the existing event.

**401** — not authenticated. **422** — invalid coordinates.

### `GET /api/v1/emergency/{id}`

Fetch one emergency event. **Auth required.** Only the owner may read it.

**200**
```json
{ "success": true,
  "data": { "id": 42, "event_type": "sos", "status": "active",
            "latitude": 17.385044, "longitude": 78.486671,
            "created_at": "2026-06-25T10:05:00Z" },
  "error": null }
```

**404** — no such event **or** the event belongs to another user. The two are
deliberately indistinguishable so event ids cannot be enumerated by a non-owner
(a safety requirement — see [security-design.md](security-design.md)).

### `PATCH /api/v1/emergency/{id}/status`

Advance an emergency event through its lifecycle
(`active → acknowledged → resolved / cancelled`). **Auth required.** Owner only.

**Request**
```json
{ "status": "acknowledged" }
```

`status` must be one of `acknowledged`, `resolved`, `cancelled` (transitioning
*to* `active` is never permitted).

**200**
```json
{ "success": true,
  "data": { "id": 42, "event_type": "sos", "status": "acknowledged",
            "latitude": 17.385044, "longitude": 78.486671,
            "created_at": "2026-06-25T10:05:00Z" },
  "error": null }
```

**409** — the lifecycle forbids the transition (e.g. reopening a resolved event):
```json
{ "success": false, "data": null,
  "error": { "code": "invalid_status_transition",
             "message": "That status change is not allowed.", "details": {} } }
```

**404** — unknown or not-owned event (indistinguishable, as above).
**422** — a value that is not a valid status.

---

## Contacts

### `POST /api/v1/contacts`

Add an emergency contact. **Auth required.**

**Request**
```json
{ "contact_name": "Amma", "phone_number": "+919876543210", "relationship": "parent" }
```

**201**
```json
{ "success": true,
  "data": { "id": 7, "contact_name": "Amma", "phone_number": "+919876543210", "relationship": "parent" },
  "error": null }
```

**409** — duplicate number for this user (`duplicate_contact`).
**422** — phone not E.164.

### `GET /api/v1/contacts`

List the authenticated user's contacts. **Auth required.** Paginated.

**Query**: `?page=1&limit=20`

**200**
```json
{ "success": true,
  "data": [
    { "id": 7, "contact_name": "Amma", "phone_number": "+919876543210", "relationship": "parent" }
  ],
  "error": null,
  "meta": { "total": 1, "page": 1, "limit": 20 } }
```

---

## Location

### `POST /api/v1/location/update`

Record the user's current position. **Auth required.**

**Request**
```json
{ "latitude": 17.385044, "longitude": 78.486671 }
```

**201**
```json
{ "success": true,
  "data": { "id": 901, "latitude": 17.385044, "longitude": 78.486671, "timestamp": "2026-06-25T10:06:00Z" },
  "error": null }
```

### `GET /api/v1/location/history`

Return recent positions, newest first. **Auth required.** Paginated.

**Query**: `?page=1&limit=50`

**200**
```json
{ "success": true,
  "data": [
    { "id": 901, "latitude": 17.385044, "longitude": 78.486671, "timestamp": "2026-06-25T10:06:00Z" }
  ],
  "error": null,
  "meta": { "total": 1, "page": 1, "limit": 50 } }
```

---

## AI

### `POST /api/v1/risk/analyze`

Score the risk of a location/time. **Auth required.**

**Request**
```json
{ "latitude": 17.385044, "longitude": 78.486671, "context": { "hour": 22, "is_alone": true } }
```

**200**
```json
{ "success": true,
  "data": { "risk_score": 0.78, "band": "high", "model_version": "risk-clf-0.1.0",
            "recommendations": [
              "Share your live location with a trusted contact.",
              "Prefer well-lit main roads; avoid shortcuts.",
              "Keep your phone unlocked for a one-tap SOS."
            ] },
  "error": null }
```

`band` is derived from `risk_score`: `low` (< 0.34), `moderate` (0.34–0.66),
`high` (> 0.66).

### `GET /api/v1/recommendations`

Return the user's recent safety recommendations. **Auth required.** Paginated.

**200**
```json
{ "success": true,
  "data": [
    { "id": 11, "recommendation": "Share your live location with a trusted contact.", "created_at": "2026-06-25T10:07:00Z" }
  ],
  "error": null,
  "meta": { "total": 1, "page": 1, "limit": 20 } }
```

---

## Notes for implementers

- **Validation** is enforced by pydantic request models; field errors surface as
  `422` with a `details` map.
- **Authorization** is checked in the use case/route: a user can only access
  their own contacts, events, locations, and recommendations.
- **Idempotency** applies to `POST /emergency/sos` via the `Idempotency-Key`
  header (see [glossary](glossary.md#idempotency)).
- **Timestamps** are ISO-8601 UTC (`Z` suffix).
- This contract is versioned under `/api/v1`; breaking changes ship under a new
  version prefix.
