# Development Roadmap

SafeAI is built in **incremental, shippable phases**. Each phase has a clear
goal, a concrete deliverable, and a "definition of done" gated by tests and CI.
This sequencing front-loads the engineering foundation so every later feature is
built on solid, tested ground — the way a production system grows.

> Status legend: ✅ done · 🟡 in progress · ⬜ planned

---

## Phase 1 — Engineering Foundation ✅

**Goal:** a runnable, tested, containerized skeleton with the architecture in
place — before any feature logic.

**Deliverables**

- FastAPI application via an **application factory** (`create_app`).
- Typed **configuration** (`pydantic-settings`, env-driven, fail-fast).
- Structured **logging** setup.
- **Health endpoints** — separate `/api/v1/health/live` (liveness) and
  `/api/v1/health/ready` (DB-aware readiness).
- **Global exception handlers** enforcing the response envelope on every path.
- **Database connection** + SQLAlchemy 2.x session management.
- **Alembic** initialized for migrations.
- **Security utilities** — password hashing (bcrypt) + JWT encode/decode.
- **Clean Architecture** package skeleton (`domain/application/infrastructure/api/core`).
- **Testing framework** (pytest) with first unit + API tests.
- Frontend: Next.js + TypeScript scaffold, landing/health page, API client stub.
- Infra: Dockerfile(s), `docker-compose.yml` (API + Postgres).
- CI: lint (ruff) · type-check (mypy) · tests (pytest) · frontend lint/build · Docker build.

**Definition of done**

- `ruff`, `mypy`, `pytest` pass with no warnings; frontend `lint`/`build` pass.
- `docker compose up` starts API + DB; `/api/v1/health/ready` returns `ready`.
- No secrets committed; `.env` ignored.

---

## Phase 2 — Authentication & User Management ✅

**Goal:** real users can register, log in, and read their profile.

**Deliverables**

- `users` table + Alembic migration.
- Domain: `User` entity, `UserRepository` port; application: `RegisterUserUseCase`,
  `AuthenticateUserUseCase`.
- Infrastructure: SQLAlchemy `User` model + repository.
- API: `POST /auth/register`, `POST /auth/login`, `GET /profile`.
- JWT issuance + an auth dependency that resolves the current user.
- Tests: password hashing, token round-trip, register/login/profile flows,
  duplicate-email conflict, invalid-credentials.

**Definition of done:** auth flow works end-to-end with tests; no plaintext
passwords anywhere; ≥80% coverage on new code.

---

## Phase 3 — Emergency Workflow ⬜

**Goal:** users can trigger an SOS that is durably recorded and notifies contacts.

**Deliverables**

- `emergency_contacts`, `emergency_events` tables + migrations.
- Domain: `EmergencyContact`, `EmergencyEvent` entities with **status lifecycle**
  rules; `EmergencyContactRepository`, `EventRepository`, `Notifier` ports.
- Application: `AddContactUseCase`, `ListContactsUseCase`, `TriggerSosUseCase`
  (write-first, then best-effort notify), `GetEventUseCase`.
- Infrastructure: repositories + `LogNotifier` adapter.
- API: `POST /contacts`, `GET /contacts`, `POST /emergency/sos` (idempotent),
  `GET /emergency/{id}`.
- Tests: status transitions, **idempotency** of SOS, per-user authorization,
  notify-after-persist ordering.

**Definition of done:** SOS creates exactly one event per idempotency key,
persists before notifying, and only the owner can read events.

---

## Phase 4 — Location Tracking ⬜

**Goal:** record and retrieve a user's location history.

**Deliverables**

- `location_history` table + migration (designed for time partitioning).
- Domain/application: `RecordLocationUseCase`, `GetLocationHistoryUseCase`.
- API: `POST /location/update`, `GET /location/history` (paginated, newest-first).
- Tests: ordering, pagination, per-user isolation, coordinate validation.

**Definition of done:** history is correctly ordered, paginated, and isolated
per user; coordinate ranges enforced.

---

## Phase 5 — AI Risk Prediction ⬜

**Goal:** score location risk and produce explainable recommendations.

**Deliverables**

- `risk_assessments`, `safety_recommendations` tables + migrations.
- ML: a `FeatureBuilder` (shared train/serve), a scikit-learn classifier, a
  training script, persisted model artifact, and `model_version` tracking.
- Domain: `RiskAssessor`, `RecommendationService` ports; `RiskScore` value object.
- Application: `AssessRiskUseCase` (features → score → persist → recommend).
- Infrastructure: `SklearnRiskAssessor` implementing the port.
- API: `POST /risk/analyze`, `GET /recommendations`.
- Tests: deterministic feature building, score in [0,1], band thresholds,
  model load/predict, recommendation rules. (See ML testing in
  [testing-strategy.md](testing-strategy.md).)

**Definition of done:** scores are reproducible for a given model version;
recommendations are deterministic; model tests pass in CI.

---

## Phase 6 — Dashboard & Deployment ⬜

**Goal:** a usable web dashboard and a production-shaped deployment.

**Deliverables**

- Frontend: auth screens, contact management, SOS button, location view, risk
  dashboard consuming the v1 API via the typed client.
- Hardening: rate limiting (login/SOS), security headers, refined error UX.
- Deployment: production Docker build, environment configuration docs,
  (optional) PostGIS enablement and managed-Postgres notes.
- Observability: request logging, health/readiness wired to orchestration.

**Definition of done:** a reviewer can register, add a contact, trigger an SOS,
view location/risk, and see notifications in logs — end-to-end, from the browser.

---

## Sequencing rationale

- **Foundation before features.** Phase 1 ensures everything after it is tested,
  typed, and reproducible — mirroring how real systems are bootstrapped.
- **Auth before everything user-owned.** Phases 3–5 all depend on "the current
  user," so authentication lands first.
- **Data before AI.** Location history (Phase 4) feeds risk features (Phase 5).
- **UI last.** The dashboard (Phase 6) integrates already-proven APIs rather
  than racing ahead of them.

Each phase is independently demoable and leaves `main` green.
