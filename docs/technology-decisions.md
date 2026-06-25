# Technology Decisions

This document records *why* each major technology was chosen. The format for
every decision is deliberate: **alternatives considered → why selected →
trade-offs accepted**. The intent is to show engineering judgment, not just a
stack list. Decisions are written in the spirit of a lightweight ADR
(Architecture Decision Record).

---

## 1. Backend framework — **FastAPI**

**Alternatives considered**

- **Django / Django REST Framework** — batteries-included, mature admin & ORM.
- **Flask** — minimal, huge ecosystem, but unopinionated and sync-first.
- **FastAPI** — async-native, typed, automatic OpenAPI.

**Why selected**

- **Type-first & validation built in.** Pydantic models give request/response
  validation and self-documenting schemas with no extra layer. This aligns
  directly with our Clean Architecture DTO boundary.
- **Async-native.** A safety platform does I/O-bound work (DB, notifications,
  inference calls). FastAPI's ASGI/async model handles concurrency well.
- **Automatic OpenAPI/Swagger.** Free, always-accurate API docs — valuable for
  a portfolio and for frontend integration.
- **Lightweight & unopinionated about structure.** Lets us impose Clean
  Architecture rather than fighting a framework's conventions (Django's
  app/model coupling would push against a framework-free domain).

**Trade-offs accepted**

- No built-in admin or ORM — we add SQLAlchemy + Alembic deliberately.
- Smaller "convention" surface than Django means we own more structure (which
  is exactly what we want here, but it is more upfront design work).

---

## 2. Database — **PostgreSQL**

**Alternatives considered**

- **MySQL** — popular, solid, but weaker on advanced types and extensions.
- **MongoDB** — flexible documents, but our data is highly relational
  (users → contacts → events → locations) and needs constraints.
- **SQLite** — great for tests/dev, not for concurrent production writes.
- **PostgreSQL** — relational, standards-compliant, rich extension ecosystem.

**Why selected**

- **Relational integrity matters.** Foreign keys, unique constraints, and
  transactions protect the integrity of emergency data — we cannot afford an
  orphaned event or a lost contact link.
- **PostGIS.** First-class geospatial support is a natural fit for a
  location-centric safety product (spatial indexes, distance queries).
- **JSONB when we need it.** We get schema-on-write *and* the option of
  semi-structured fields (e.g. risk feature snapshots) without a second store.
- **Operational maturity.** Replication, partitioning, and a deep tooling
  ecosystem give a real scaling path.

**Trade-offs accepted**

- Heavier to run locally than SQLite — mitigated with Docker Compose.
- Requires migration discipline (Alembic) vs schema-less stores.

---

## 3. ORM & migrations — **SQLAlchemy 2.x + Alembic**

**Alternatives considered**

- **Raw SQL / asyncpg only** — maximum control, maximum boilerplate, easy to
  introduce injection or inconsistency.
- **Tortoise ORM / SQLModel** — async-friendly, but smaller ecosystems;
  SQLModel blurs the DTO/ORM line we want to keep separate.
- **SQLAlchemy 2.x** — the de-facto Python ORM, now with a modern typed API.

**Why selected**

- **Parameterized queries by default** → SQL injection is structurally
  prevented.
- **2.x typed `Mapped[...]` style** integrates cleanly with our typed codebase
  and mypy.
- **Repository pattern fit.** SQLAlchemy lives entirely in `infrastructure`,
  implementing domain repository interfaces — the domain never imports it.
- **Alembic** gives versioned, reviewable, reversible schema migrations —
  essential for a project meant to evolve across phases.

**Trade-offs accepted**

- Learning curve and some ceremony vs raw SQL.
- We must consciously keep ORM models out of the domain (enforced by layering).

---

## 4. Validation & settings — **Pydantic v2 / pydantic-settings**

**Why selected**

- One consistent validation model for API DTOs *and* application config.
- `pydantic-settings` loads typed configuration from the environment and
  **fails fast** when a required secret is missing — exactly the secure-config
  behavior we want.
- v2's Rust core is fast enough to validate on the hot path.

**Trade-offs accepted**

- Pydantic v2 changed some v1 APIs; we standardize on v2 throughout to avoid
  mixing idioms.

---

## 5. Containerization — **Docker + Docker Compose**

**Alternatives considered**

- **Local installs (venv + local Postgres)** — fastest to start, but
  "works on my machine" drift and painful onboarding.
- **Kubernetes** — production-grade orchestration, but massive overkill for a
  single-service project at this stage (premature complexity).
- **Docker Compose** — reproducible multi-service local environment.

**Why selected**

- **Reproducibility.** One command brings up API + PostgreSQL with pinned
  versions. The repo can be evaluated on any machine identically — and this
  matters because the project will be moved between laptops.
- **Parity.** Dev mirrors prod topology (app + database) closely.
- **Right altitude.** Compose is the correct tool for one app + one DB; we
  explicitly avoid Kubernetes until there is a reason for it.

**Trade-offs accepted**

- Image build time and Docker as a prerequisite.
- Compose is not a production orchestrator — but it is honest about that, and
  the Dockerfile is reusable by whatever orchestrator comes later.

---

## 6. Frontend — **Next.js + TypeScript + Tailwind CSS**

**Alternatives considered**

- **Plain React (Vite SPA)** — simple, but no SSR/routing conventions.
- **Vue / SvelteKit** — capable, but React/Next is the broadest, most
  recognizable stack for a portfolio aimed at large-scale employers.
- **Next.js** — React framework with routing, SSR/SSG, and strong conventions.

**Why selected**

- **TypeScript end-to-end** pairs with our typed backend for safer integration.
- **Conventions reduce bikeshedding** — file-based routing, clear data-fetching
  patterns, first-class deployment story.
- **Tailwind** gives fast, consistent UI without a sprawling custom CSS layer,
  keeping the frontend focused on the safety UX (SOS, contacts, dashboard).

**Trade-offs accepted**

- Next.js has more concepts than a bare SPA; we use only what the dashboard
  needs and avoid over-using server components prematurely.
- Tailwind's utility classes are verbose in markup (accepted for velocity).

---

## 7. Machine learning — **scikit-learn (+ pandas, numpy)**

**Alternatives considered**

- **Deep learning (PyTorch/TensorFlow)** — powerful, but overkill for tabular
  risk scoring; heavier to train, serve, and explain.
- **A hosted ML API** — fast to start, but adds cost, latency, a vendor
  dependency, and sends sensitive location data off-platform.
- **scikit-learn** — classical ML for tabular data.

**Why selected**

- **Right tool for tabular risk data.** Location/time/context features map to a
  classic classification problem; tree/linear models are strong baselines.
- **Explainability.** Simpler models + feature importances make safety
  recommendations defensible — important when advice affects real people.
- **In-process serving.** No extra infrastructure; the model loads behind the
  `RiskAssessor` port and can be extracted later if needed.
- **Reproducibility.** Lightweight to version (`model_version`) and retrain.

**Trade-offs accepted**

- Lower ceiling than deep learning on complex/unstructured signals — acceptable;
  we can swap the port implementation if requirements grow.
- Requires disciplined feature engineering to avoid train/serve skew (addressed
  with a shared `FeatureBuilder`).

---

## 8. Testing — **pytest (+ httpx, coverage)**

**Why selected**

- The standard, expressive Python test framework; fixtures model our DI cleanly.
- Domain/use-case tests need no framework; integration tests use a real
  Postgres (via Compose/CI) for fidelity; API tests use FastAPI's test client.
- Coverage tooling enforces our ≥80% target.

**Trade-offs accepted**

- Real-database integration tests are slower than pure mocks — accepted for the
  confidence they provide on the data layer.

---

## 9. CI — **GitHub Actions**

**Why selected**

- Native to where the project will live; zero extra accounts.
- Encodes our quality gate as code: lint (ruff), type-check (mypy), tests
  (pytest), frontend lint/build, and Docker build — every push.

**Trade-offs accepted**

- Vendor-specific YAML; acceptable given GitHub is the target host.

---

## 10. Linting & typing — **ruff + mypy**

**Why selected**

- **ruff** is an extremely fast linter/formatter that consolidates many tools
  (flake8, isort, pyupgrade) into one, keeping CI quick.
- **mypy** enforces the static typing that the whole design leans on; type
  errors are caught before runtime.

**Trade-offs accepted**

- Strict typing requires annotations discipline — a feature, not a bug, for a
  codebase meant to demonstrate rigor.

---

## Decision summary

| Area | Choice | One-line rationale |
|------|--------|--------------------|
| API framework | FastAPI | Typed, async, auto-docs, structure-agnostic |
| Database | PostgreSQL | Relational integrity + PostGIS + scaling path |
| ORM/migrations | SQLAlchemy 2.x + Alembic | Safe queries, typed, versioned schema |
| Validation/config | Pydantic v2 | One model for DTOs + fail-fast config |
| Containers | Docker + Compose | Reproducible, right altitude (not k8s) |
| Frontend | Next.js + TS + Tailwind | Typed, conventional, fast UI |
| ML | scikit-learn | Right fit for tabular, explainable, in-process |
| Tests | pytest | Standard, fixtures match our DI |
| CI | GitHub Actions | Native quality gate as code |
| Lint/type | ruff + mypy | Fast lint + enforced static typing |
