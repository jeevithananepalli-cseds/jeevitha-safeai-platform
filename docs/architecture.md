# SafeAI — System Architecture

> Intelligent Women's Safety & Emergency Response Platform

This document describes the architecture of SafeAI: the layering strategy, the
core workflows, the security posture, and how the system is intended to scale.
Every decision below is justified — the goal is a design that a reviewer can
read and understand *why*, not just *what*.

> **Scope note:** this is the **target architecture**. It describes the full
> system design, including workflows (SOS, notifications, AI risk) that are
> planned for later phases. For what is implemented today, see
> [development-roadmap.md](development-roadmap.md) — currently the engineering
> foundation (Phase 1) and authentication (Phase 2).

---

## 1. System Overview

SafeAI helps a user get help quickly during an emergency. The platform provides:

- **SOS activation** — a single action that records an emergency event and
  notifies the user's trusted contacts with their location.
- **Emergency contact management** — the people who should be notified.
- **Location sharing & history** — the user's recent positions, used both for
  live sharing and for risk modeling.
- **Emergency event tracking** — a durable, auditable record of every SOS,
  its status, and its resolution.
- **AI risk assessment** — a model that scores how risky a location/time is.
- **Safety recommendations** — actionable guidance derived from risk signals.

The system is delivered as:

- A **FastAPI** backend exposing a versioned REST API (`/api/v1/...`).
- A **PostgreSQL** database (PostGIS-ready for future geospatial queries).
- A **scikit-learn** model served in-process by the backend.
- A **Next.js** frontend for registration, contact management, and a dashboard.

```
                         ┌──────────────────────────┐
                         │        Next.js Web        │
                         │   (TypeScript, Tailwind)  │
                         └────────────┬─────────────┘
                                      │ HTTPS / REST (JSON)
                                      ▼
                         ┌──────────────────────────┐
                         │      FastAPI Backend      │
                         │  api → application →      │
                         │  domain ← infrastructure  │
                         └─────┬───────────────┬─────┘
                               │               │
                   ┌───────────▼───┐     ┌─────▼──────────┐
                   │  PostgreSQL    │     │  ML Risk Model │
                   │  (+ PostGIS)   │     │  (scikit-learn)│
                   └────────────────┘     └────────────────┘
```

---

## 2. Clean Architecture

SafeAI uses **Clean Architecture** (a.k.a. Ports & Adapters / Hexagonal). The
codebase is split into concentric layers. The single most important rule:

> **The Dependency Rule:** source code dependencies point *inward only*.
> Inner layers know nothing about outer layers.

```
        ┌─────────────────────────────────────────────────┐
        │  api/   (HTTP controllers, request/response DTOs)│   ← framework
        │   ┌─────────────────────────────────────────┐   │
        │   │ application/ (use cases, orchestration)  │   │   ← app rules
        │   │   ┌─────────────────────────────────┐   │   │
        │   │   │ domain/ (entities, rules,        │   │   │   ← enterprise
        │   │   │          repository interfaces)  │   │   │     rules
        │   │   └─────────────────────────────────┘   │   │
        │   └─────────────────────────────────────────┘   │
        │  infrastructure/ (DB, ML, external services)     │   ← adapters
        └─────────────────────────────────────────────────┘
              core/  (config, security, logging) — cross-cutting
```

### 2.1 Layer responsibilities

| Layer | Contains | Depends on | Must NOT depend on |
|-------|----------|------------|--------------------|
| `domain` | Entities (`User`, `EmergencyEvent`, …), value objects, domain rules, **repository interfaces (ports)** | nothing (pure Python) | FastAPI, SQLAlchemy, pydantic models |
| `application` | Use cases / application services (e.g. `TriggerSosUseCase`), orchestration, DTOs between layers | `domain` | `api`, `infrastructure` concretions |
| `infrastructure` | SQLAlchemy repositories, ML service, notifier adapters, Alembic | `domain` (implements ports) | `api` |
| `api` | FastAPI routers, request/response pydantic schemas, dependency wiring | `application`, `domain` | — |
| `core` | Settings, security (hashing/JWT), logging, DB session factory | stdlib + minimal libs | business logic |

### 2.2 Why this matters for SafeAI

- **The domain is framework-free.** `EmergencyEvent` is plain Python. We can
  unit-test SOS rules with zero database, zero HTTP, zero mocks of frameworks.
- **Swappable adapters.** Today notifications might be a log line; tomorrow
  Twilio SMS. The domain defines a `Notifier` port; only an adapter changes.
- **Swappable ML.** The risk model is behind a `RiskAssessor` port. We can move
  from scikit-learn in-process to a remote inference service without touching
  use cases.
- **Testability is structural, not aspirational.** Because dependencies are
  injected as interfaces, fakes are trivial.

### 2.3 Dependency injection

Wiring happens at the **edge** (`api` / app startup), not in the core. FastAPI's
dependency system (`Depends`) supplies a repository implementation to a use case.
The use case only sees the interface. This keeps the composition root in one
place and the inner layers ignorant of concrete choices.

Concretely, the **application factory** (`create_app(settings)`) is the
composition root: it builds the `Database` (engine + session factory) from the
*injected* settings and stores both on `app.state`. The dependency providers in
`app/api/deps.py` (`get_app_settings`, `get_database`, `get_session`) resolve
these from the request, so request handlers never read a module-level global.
Two consequences: (1) configuration injected into the factory genuinely reaches
the database layer; (2) tests substitute any dependency via
`app.dependency_overrides` (e.g. forcing the readiness check to report the
database as down). There is **no import-time engine singleton**.

---

## 3. Component Diagram

```
api/
  v1/
    routes/
      health.py        ─┐
      auth.py           │  thin controllers: validate input,
      contacts.py       │  call a use case, shape the response
      emergency.py      │
      location.py       │
      risk.py          ─┘
    schemas/            request/response pydantic models (DTOs)

application/
  use_cases/
    register_user.py
    trigger_sos.py
    assess_risk.py
    ...                 orchestrate domain + ports, no framework code

domain/
  entities/            User, EmergencyContact, EmergencyEvent, ...
  value_objects/       Coordinates, RiskScore, PhoneNumber
  repositories/        UserRepository, EventRepository (interfaces)
  services/            RiskAssessor, Notifier (interfaces / ports)

infrastructure/
  db/
    models/            SQLAlchemy ORM models (mapped to tables)
    repositories/      concrete repos implementing domain interfaces
    session.py
  ml/
    risk_model.py      scikit-learn RiskAssessor implementation
  notifications/
    log_notifier.py    dev notifier (later: sms_notifier.py)

core/
  config.py            pydantic-settings, env-driven
  security.py          password hashing, JWT encode/decode
  logging.py           structured logging setup
```

---

## 4. SOS Workflow

The SOS flow is the heart of the product. It must be **fast, durable, and
idempotent** (a panicked user may tap twice — we must not create two events or
double-notify in a way that harms clarity).

```
User taps SOS
     │
     ▼
POST /api/v1/emergency/sos  ──►  api: validate auth (JWT) + payload
     │                                   │
     │                                   ▼
     │                          TriggerSosUseCase.execute(user_id, location)
     │                                   │
     │            ┌──────────────────────┼───────────────────────────┐
     │            ▼                       ▼                           ▼
     │   1. Create EmergencyEvent   2. Snapshot location      3. Resolve contacts
     │      (status = ACTIVE)          into location_history     for the user
     │      (idempotency key)
     │            │
     │            ▼
     │   4. Notifier.notify(contacts, event)  ── async / best-effort
     │            │
     │            ▼
     │   5. Persist event + return event id, status, timestamp
     ▼
Response: 201 Created  { event_id, status: "active", notified: N }
```

**Design notes**

- **Idempotency:** the client sends an `Idempotency-Key`. The use case checks
  for an existing event with that key before creating a new one — a retry
  returns the same event. (See [glossary](glossary.md#idempotency).)
- **Write-first, notify-after:** the event is durably persisted *before* we
  attempt notification. If notification fails, the event still exists and can
  be retried; we never lose the record of a real emergency.
- **Status lifecycle:** `ACTIVE → ACKNOWLEDGED → RESOLVED` (or `CANCELLED`).
  Status transitions are validated in the domain entity, not in the controller.

---

## 5. Emergency Notification Flow

Notification is modeled as a **port** (`Notifier`) so the transport can evolve.

```
TriggerSosUseCase
     │  contacts = EmergencyContactRepository.list_for_user(user_id)
     ▼
Notifier.notify(event, contacts)
     │
     ├── Phase 1–3:  LogNotifier      → structured log entry (audit + dev)
     ├── Future:     SmsNotifier      → Twilio / SNS
     └── Future:     PushNotifier     → FCM / APNs
```

- Each contact notification is **best-effort and independent** — one failing
  number must not block the others.
- Delivery attempts are intended to be **recorded** (future: `notification_log`
  table) so we can prove a contact was reached.
- For scale, notification can be moved **off the request path** onto a queue
  (e.g. the use case enqueues; a worker delivers). The port boundary makes this
  a non-breaking change.

---

## 6. AI Risk Assessment Flow

```
POST /api/v1/risk/analyze   { latitude, longitude, time, context }
     │
     ▼
AssessRiskUseCase.execute(request)
     │   features = FeatureBuilder.build(location, time, history)
     ▼
RiskAssessor.score(features)        ◄── port (interface)
     │        implemented by infrastructure/ml/risk_model.py
     │        scikit-learn classifier → probability → RiskScore (0..1)
     ▼
Persist RiskAssessment (score, model_version)
     │
     ▼
RecommendationService.derive(risk_score, context)
     │
     ▼
Response: { risk_score, band: low|moderate|high, recommendations[] }
```

**Design notes**

- The model is **versioned** (`model_version` is stored with every assessment)
  so predictions are reproducible and auditable.
- The classifier is behind the `RiskAssessor` port. The use case is agnostic to
  whether scoring is local scikit-learn or a remote service.
- Features are derived deterministically by a `FeatureBuilder` so training and
  serving use the same logic (avoids train/serve skew).
- Recommendations are rule-driven on top of the model output, keeping ML
  outputs explainable and the safety advice deterministic.

---

## 7. Security Architecture

Security is a first-class concern for a safety product handling location data.
This section summarizes the controls; the full **threat model, abuse cases, and
privacy-by-design analysis** live in [security-design.md](security-design.md).

| Concern | Approach |
|---------|----------|
| **Password storage** | Hashed with bcrypt (via `passlib`). Plaintext never stored or logged. |
| **Authentication** | Stateless **JWT** access tokens, signed with an env-provided secret (HS256). No secret in source. |
| **Authorization** | Every protected route resolves the current user from the token; users can only read/write their own contacts, events, and location. |
| **Input validation** | All inbound payloads validated by pydantic schemas at the API boundary. Reject malformed/oversized input early. |
| **Secrets** | Loaded from environment via `pydantic-settings`. `.env` is git-ignored; `.env.example` documents required keys with no real values. |
| **Transport** | HTTPS in production (terminated at the proxy/load balancer). |
| **SQL injection** | Eliminated by SQLAlchemy parameterized queries / ORM. |
| **PII minimization** | Location history is retained with a defined strategy (future TTL); only necessary fields are persisted. |
| **Error hygiene** | Enforced by global exception handlers (`app/api/errors.py`): validation, HTTP, and unhandled errors all return the standard envelope with a safe message; stack traces and internal detail are logged server-side, never returned to clients. |
| **Rate limiting** | Planned at the edge (reverse proxy) and per-sensitive-endpoint (e.g. login) to resist brute force and abuse. |

**Threat-model highlights**

- *Account takeover* → strong hashing + JWT expiry + (future) refresh rotation.
- *Location leakage* → per-user authorization on every location/event read.
- *SOS abuse / spam* → idempotency + rate limiting on `/emergency/sos`.

---

## 8. Scalability Considerations

The design is a **modular monolith** — intentionally *not* microservices. For a
project at this stage, a well-layered monolith gives the best ratio of
clarity to capability. The layering, however, makes future extraction cheap.

**Where load concentrates and how we address it**

1. **Stateless API** — the backend holds no session state (JWT is stateless),
   so it scales **horizontally** behind a load balancer. Add instances to add
   capacity.
2. **Database** — the read/write hotspots are `emergency_events` and
   `location_history`. We index by `user_id` and time, partition `location_history`
   by time as it grows, and add read replicas for analytics/risk features.
3. **Notifications** — moved off the request path to a queue + workers when
   volume grows. The `Notifier` port makes this transparent to use cases.
4. **ML inference** — in-process today; extractable to a dedicated inference
   service behind the `RiskAssessor` port if model size/latency demands it.
5. **Geospatial** — PostGIS enables efficient "events/risk near a point"
   queries with spatial indexes (GiST) instead of full scans.

**Guiding principle:** scale by *moving a boundary that already exists*, not by
rewriting. Clean Architecture is what makes that possible.

---

## 9. Cross-Cutting Concerns

- **Configuration** — single typed `Settings` object, environment-driven,
  validated at startup (fail fast on missing secrets).
- **Logging** — structured logs with request context; no secrets/PII in logs.
- **Health** — separate probes: `/api/v1/health/live` (liveness, no
  dependencies — targeted by the container healthcheck) and
  `/api/v1/health/ready` (DB-aware readiness, `503` + `success=false` when a
  dependency is down — for load-balancer routing). Separating them prevents a
  transient database outage from causing an orchestrator to kill a healthy API.
- **Migrations** — Alembic; schema changes are versioned and reviewable.
- **Testing** — unit (domain/use cases), integration (repositories/API), and
  ML model tests. See [testing-strategy.md](testing-strategy.md).

---

## 10. Summary

SafeAI is a layered, framework-independent core wrapped by replaceable adapters.
The domain encodes safety rules in plain Python; FastAPI, SQLAlchemy, and
scikit-learn are details at the edges. This buys testability, explainability,
and a credible scaling path — without paying the complexity tax of premature
microservices.
