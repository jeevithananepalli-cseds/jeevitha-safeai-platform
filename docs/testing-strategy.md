# Testing Strategy

Testing is structural in SafeAI, not an afterthought. Clean Architecture makes
the inner layers trivially testable (no frameworks to mock), and the outer
layers are tested against real adapters where fidelity matters (a real Postgres,
the real FastAPI app). The target is **≥80% coverage**, but coverage is a
floor, not the goal — the goal is *confidence that emergency behavior is correct*.

---

## 1. The Test Pyramid

```
            ╱╲      E2E / API flow (few)        ← FastAPI TestClient end-to-end
           ╱──╲     Integration (some)          ← repositories vs real Postgres
          ╱────╲    ML model tests (focused)    ← features, scoring, versioning
         ╱──────╲   Unit (many, fast)           ← domain entities + use cases
        ╱────────╲
```

Most tests are fast unit tests of the domain and use cases. Fewer, heavier tests
verify the seams (DB, HTTP). This keeps the suite fast and the signal high.

---

## 2. Unit Testing — domain & use cases

**Scope:** entities, value objects, domain rules, and application use cases.

- The domain is **pure Python**, so these tests need no DB, no HTTP, no mocks of
  frameworks. Example: `EmergencyEvent` enforces valid status transitions
  (`active → resolved` ok; `resolved → active` rejected).
- Use cases are tested with **in-memory fake repositories** implementing the
  domain ports. Example: `TriggerSosUseCase` is verified to **persist before
  notifying** and to be **idempotent** for a repeated `Idempotency-Key`, using a
  fake repo + fake notifier — no database involved.

**Why this works:** because dependencies are injected as interfaces, fakes are a
few lines. We test *behavior and rules*, not wiring.

---

## 3. Integration Testing — repositories & DB

**Scope:** SQLAlchemy repositories and migrations against a **real PostgreSQL**.

- Run against a Postgres provided by Docker Compose locally and a service
  container in CI — not SQLite — so constraints, types, and SQL behave as in prod.
- Each test runs in a **transaction rolled back** at teardown (fast, isolated),
  or against an ephemeral schema.
- Verifies: constraints fire (unique email, unique idempotency key, coordinate
  CHECKs), cascades behave, indexes/queries return correctly ordered results.
- Alembic migrations are applied to a clean database in CI to prove they run.

---

## 4. API Testing — request/response & auth

**Scope:** the HTTP boundary via FastAPI's `TestClient`/`httpx.AsyncClient`.

- Validates: status codes, the response envelope, validation errors (`422`),
  auth enforcement (`401`/`403`), and the success payloads in
  [api-contract.md](api-contract.md).
- Covers critical flows end-to-end against a test database: register → login →
  authenticated profile; add contact → list; trigger SOS → fetch event.
- Asserts **authorization isolation**: user A cannot read user B's event (`403`).
- Asserts **idempotent SOS**: same key → one event, replay returns it.

---

## 5. ML Model Testing

ML is tested like code, with model-specific checks:

- **Deterministic features.** `FeatureBuilder.build(...)` is pure and tested for
  stable output → prevents train/serve skew.
- **Contract tests.** `RiskAssessor.score(features)` always returns a float in
  `[0, 1]`; band thresholds (`low/moderate/high`) map correctly at boundaries.
- **Artifact load.** The persisted model loads and predicts on a known sample
  with an expected shape/range (a smoke test, not a brittle exact-value test).
- **Versioning.** Every assessment records `model_version`; tests assert it is
  attached and surfaced in responses.
- **Baseline quality (offline).** A held-out evaluation reports metrics
  (accuracy / ROC-AUC) above an agreed threshold; this guards regressions when
  retraining. Recommendations are rule-based and unit-tested deterministically.

---

## 6. CI Testing

Every push runs the full quality gate via GitHub Actions
(see [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)):

| Stage | Tool | Gate |
|-------|------|------|
| Lint (backend) | `ruff check` | no lint errors |
| Format check | `ruff format --check` | consistent formatting |
| Type check | `mypy` | no type errors |
| Unit + integration | `pytest` (with Postgres service) | all pass |
| Coverage | `pytest --cov` | ≥ 80% |
| Frontend lint | `next lint` / `eslint` | no errors |
| Frontend build | `next build` | builds clean |
| Container | `docker build` | image builds |

A red gate blocks merge. The same commands run locally, so "green on my machine"
means "green in CI."

---

## 7. Test Data & Fixtures

- **Fixtures** (pytest) provide a DB session, a test client, and factory helpers
  for users/contacts/events — mirroring the dependency-injection wiring.
- **Fakes over mocks** for ports (in-memory repos/notifier) keep unit tests
  readable and refactor-resilient.
- **No real secrets** in tests; config uses test env values. No external network
  calls in unit tests; integration tests talk only to the local/CI Postgres.

---

## 8. What we deliberately do *not* test (yet)

- Real SMS/push delivery (the `Notifier` is a log adapter until a real transport
  is added; the port boundary is what we test).
- Load/performance testing — deferred to Phase 6 hardening.

---

## 9. Coverage philosophy

≥80% line coverage is enforced, but priority is given to:

1. Domain rules (status transitions, validation).
2. Use-case behavior (idempotency, persist-before-notify, authorization).
3. The auth and SOS API flows (highest user impact).

A function being covered is necessary; a *behavior* being asserted is what
actually matters.
