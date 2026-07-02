# Database Design

This document defines the SafeAI relational schema: tables, fields,
relationships, constraints, indexing strategy, and how the design is meant to
scale. The target engine is **PostgreSQL** (PostGIS-ready).

Design principles:

- **Integrity first** — foreign keys and constraints enforce that emergency
  data is always consistent (no orphan contacts, no event without a user).
- **Auditable & append-friendly** — events and location history are written,
  not overwritten, so we keep a faithful record of what happened.
- **Indexed for the real queries** — we index for the access patterns the app
  actually performs (per-user, recent-first, by status).
- **Scale by partition & replica**, not by rewrite.

---

## 1. Entity-Relationship Overview

```
                 ┌──────────────┐
                 │    users     │
                 └──────┬───────┘
                        │ 1
        ┌───────────────┼───────────────┬─────────────────┐
        │ N             │ N             │ N               │ N
┌───────▼────────┐ ┌────▼──────────┐ ┌─▼───────────────┐ ┌▼────────────────────┐
│emergency_      │ │emergency_     │ │location_history │ │safety_              │
│contacts        │ │events         │ │                 │ │recommendations      │
└────────────────┘ └───────────────┘ └─────────────────┘ └─────────────────────┘

risk_assessments  (location-scoped; optionally linked to a user/event)
```

Cardinality summary:

- A **user** has many **emergency_contacts**.
- A **user** has many **emergency_events**.
- A **user** has many **location_history** rows.
- A **user** has many **safety_recommendations**.
- **risk_assessments** are produced for locations (and may reference the
  requesting user / triggering event).

---

## 2. Tables

Conventions used below:

- All tables use a surrogate **`id`** primary key (`BIGINT`/`UUID`).
- Timestamps are stored as `TIMESTAMPTZ` (UTC).
- Coordinates are stored as `NUMERIC(9,6)` (≈0.1 m precision) until PostGIS
  `geography(Point)` is introduced (see §6).
- `ON DELETE CASCADE` is used where child rows have no meaning without the parent.

### 2.1 `users`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGINT` (identity) / `UUID` | **PK** | Surrogate key. |
| `name` | `VARCHAR(120)` | `NOT NULL` | Display name. |
| `email` | `CITEXT` / `VARCHAR(255)` | `NOT NULL`, **UNIQUE** | Case-insensitive login id. |
| `password_hash` | `VARCHAR(255)` | `NOT NULL` | bcrypt hash; **never** plaintext. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Audit. |

**Constraints / indexes**

- `UNIQUE(email)` — also backs login lookups.
- Email format validated at the application boundary (pydantic) before insert.

### 2.2 `emergency_contacts`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGINT` | **PK** | |
| `user_id` | `BIGINT` | **FK → users.id**, `NOT NULL`, `ON DELETE CASCADE` | Owner. |
| `contact_name` | `VARCHAR(120)` | `NOT NULL` | |
| `phone_number` | `VARCHAR(20)` | `NOT NULL` | Stored E.164 (`+<country><number>`). |
| `relationship` | `VARCHAR(50)` | `NULL` | e.g. parent, friend. |

**Constraints / indexes**

- `INDEX(user_id)` — list a user's contacts.
- `UNIQUE(user_id, phone_number)` — prevent duplicate contact numbers per user.
- `CHECK (phone_number ~ '^\+[1-9][0-9]{6,14}$')` — basic E.164 guard.

### 2.3 `emergency_events`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGINT` | **PK** | |
| `user_id` | `BIGINT` | **FK → users.id**, `NOT NULL`, `ON DELETE CASCADE` | |
| `event_type` | `VARCHAR(30)` | `NOT NULL` | e.g. `sos`, `check_in`. |
| `latitude` | `NUMERIC(9,6)` | `NOT NULL` | Captured at activation. |
| `longitude` | `NUMERIC(9,6)` | `NOT NULL` | |
| `status` | `VARCHAR(20)` | `NOT NULL DEFAULT 'active'` | `active`/`acknowledged`/`resolved`/`cancelled`. |
| `idempotency_key` | `VARCHAR(64)` | `NULL`, **UNIQUE** | De-dupes retried SOS taps. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | When the event was raised. |
| `updated_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | Last status change (see below). |

> **Why `updated_at`:** `status` mutates through its lifecycle
> (`active → acknowledged → resolved`). Without `updated_at` we cannot tell
> *when* an emergency was acknowledged or resolved — information that is
> essential for an auditable safety record and for response-time analytics.
> It is set to `now()` on insert and refreshed on every update. The value is
> managed application-side in the repository's update path (and may additionally
> be backed by a DB trigger). The same rationale applies to any other table
> whose rows mutate in place; append-only tables (`location_history`,
> `risk_assessments`) do not need it.
>
> The executable migration that adds this column ships with the
> `emergency_events` table itself in **Phase 3** (the table does not exist yet),
> so the column is created as part of the initial table definition rather than a
> later `ALTER`.

**Constraints / indexes**

- `INDEX(user_id, created_at)` — a user's events, most-recent-first (implemented
  as `ix_events_user_created`).
- `UNIQUE(user_id, idempotency_key)` — enforces **per-user** idempotent SOS
  creation (composite, so two users may independently use the same client key).
- *Planned Postgres hardening:* a partial `INDEX(status) WHERE status='active'`
  for the "any open emergencies?" hot query, and `CHECK` constraints on `status`
  and coordinate ranges. These are currently enforced at the application/domain
  layer (`EventStatus` enum, the `Coordinates` value object, and DTO validation)
  and kept out of the portable migration; they will be added as Postgres-only
  constraints during deployment hardening (Phase 6).

### 2.4 `location_history`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGINT` | **PK** | |
| `user_id` | `BIGINT` | **FK → users.id**, `NOT NULL`, `ON DELETE CASCADE` | |
| `latitude` | `NUMERIC(9,6)` | `NOT NULL` | |
| `longitude` | `NUMERIC(9,6)` | `NOT NULL` | |
| `timestamp` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | When the position held. |

**Constraints / indexes**

- `INDEX(user_id, timestamp DESC)` — recent track for a user / risk features.
- High-write, append-only table → **partition by month** on `timestamp` as it
  grows (see §5).
- `CHECK` on coordinate ranges as above.

### 2.5 `risk_assessments`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGINT` | **PK** | |
| `user_id` | `BIGINT` | **FK → users.id**, `NULL`, `ON DELETE SET NULL` | Optional requester. |
| `latitude` | `NUMERIC(9,6)` | `NOT NULL` | The scored location. |
| `longitude` | `NUMERIC(9,6)` | `NOT NULL` | |
| `risk_score` | `NUMERIC(4,3)` | `NOT NULL` | 0.000–1.000 probability. |
| `model_version` | `VARCHAR(40)` | `NOT NULL` | Reproducibility/audit. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | |

> The spec lists a single `location` field; we store it as explicit
> `latitude`/`longitude` (and later a PostGIS `geography(Point)`) because that
> is what the model scores and what spatial indexes require.

**Constraints / indexes**

- `INDEX(latitude, longitude)` → upgraded to a **GiST** spatial index with PostGIS.
- `INDEX(model_version)` — compare/evaluate model versions.
- `CHECK (risk_score BETWEEN 0 AND 1)`.

### 2.6 `safety_recommendations`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `BIGINT` | **PK** | |
| `user_id` | `BIGINT` | **FK → users.id**, `NOT NULL`, `ON DELETE CASCADE` | |
| `recommendation` | `TEXT` | `NOT NULL` | Human-readable advice. |
| `created_at` | `TIMESTAMPTZ` | `NOT NULL DEFAULT now()` | |

**Constraints / indexes**

- `INDEX(user_id, created_at DESC)` — recent recommendations for a user.

---

## 3. Relationships & Referential Integrity

| Parent | Child | FK | On delete | Rationale |
|--------|-------|----|-----------|-----------|
| users | emergency_contacts | `user_id` | CASCADE | A contact is meaningless without its owner. |
| users | emergency_events | `user_id` | CASCADE | Events belong to the user. |
| users | location_history | `user_id` | CASCADE | Track belongs to the user. |
| users | safety_recommendations | `user_id` | CASCADE | Advice is user-specific. |
| users | risk_assessments | `user_id` | SET NULL | Keep anonymized location-risk data for model evaluation even if a user is deleted. |

This mix is deliberate: personal data cascades away with the user (privacy),
while de-identifiable risk signals are retained for model quality.

> **Enforcement parity:** PostgreSQL enforces foreign keys by default; SQLite
> does not unless asked. The engine enables `PRAGMA foreign_keys=ON` for SQLite
> connections, so `ON DELETE CASCADE` and FK constraints behave identically in
> local/test (SQLite) and production (PostgreSQL) — and the CI test suite runs
> against PostgreSQL for full-dialect fidelity.

---

## 4. Index Strategy (summary)

Indexes are chosen from **actual query shapes**, not guessed:

| Query | Index |
|-------|-------|
| Login by email | `UNIQUE(users.email)` |
| List my contacts | `emergency_contacts(user_id)` |
| Dedupe SOS retry | `UNIQUE(emergency_events.idempotency_key)` |
| My recent events | `emergency_events(user_id, created_at DESC)` |
| Find active emergencies | partial `emergency_events(status) WHERE status='active'` |
| My recent locations | `location_history(user_id, timestamp DESC)` |
| Risk near a point | `risk_assessments` GiST (PostGIS) |
| Recommendations feed | `safety_recommendations(user_id, created_at DESC)` |

We avoid over-indexing (every index taxes writes); each index above pays for a
real, frequent read.

---

## 5. Scalability & Retention

- **`location_history` partitioning.** This is the fastest-growing table. As it
  grows, switch to **declarative range partitioning by month** on `timestamp`.
  Benefits: pruning old partitions for retention, smaller indexes, faster
  recent-window scans.
- **Retention/TTL.** Location history is sensitive PII; define a retention
  window (e.g. drop partitions older than N months) to minimize data held.
- **Read replicas.** Risk-feature computation and analytics read from replicas
  to keep the primary focused on transactional emergency writes.
- **Hot path stays small.** The operational query ("any active events?") is
  served by a small partial index and remains fast regardless of history size.
- **UUID vs BIGINT.** BIGINT identity keys by default (compact, fast). UUIDs can
  be adopted for externally exposed ids if needed; the layering keeps that an
  infrastructure detail.

---

## 6. Geospatial Roadmap (PostGIS)

Phase-5+ upgrade path, designed for now:

1. `CREATE EXTENSION postgis;`
2. Add `geography(Point, 4326)` columns to `emergency_events`,
   `location_history`, and `risk_assessments` (populated from lat/lng).
3. Add **GiST** spatial indexes.
4. Replace bounding-box math with `ST_DWithin` / `ST_Distance` for
   "events/risk near me" queries.

Because coordinates are already first-class columns and access goes through
repositories, this is an additive migration — no domain or use-case changes.

---

## 7. Migrations

All schema changes are managed by **Alembic**:

- Each change is a versioned, reviewable, reversible migration.
- The initial migration creates the tables above with their constraints/indexes.
- Migrations run in CI and on deploy; the database is never hand-edited.

See [development-roadmap.md](development-roadmap.md) for when each table is
introduced (auth tables in Phase 2, events in Phase 3, etc.).
