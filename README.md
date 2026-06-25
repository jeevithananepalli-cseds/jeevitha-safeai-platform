<div align="center">

# 🛡️ SafeAI

### Intelligent Women's Safety & Emergency Response Platform

An AI-powered platform that helps users get help fast during emergencies —
SOS activation, trusted-contact alerting, live location, and **explainable**
AI risk assessment — built with Clean Architecture, tested, and containerized.

</div>

---

## Overview

SafeAI is a full-stack safety platform. A user can trigger an **SOS** that
durably records an emergency event and notifies their trusted contacts with
their location; manage **emergency contacts**; share **location** history; and
receive **AI-driven risk scores** and actionable safety recommendations.

The codebase is intentionally engineered to production standards: a
framework-free domain core, typed boundaries, a real test suite, CI quality
gates, and documented, reasoned technology decisions.

## Problem statement

In an emergency, every second and every tap counts. Existing options are often
fragmented (separate apps for contacts, location, alerts) and offer little
proactive guidance. SafeAI unifies **reactive** safety (fast, reliable SOS) with
**proactive** safety (risk assessment and recommendations) behind one clean,
well-tested API — designed to be dependable when it matters most.

## Features

| Feature | Description |
|---------|-------------|
| 🚨 SOS activation | One action records an emergency event (idempotent) and alerts contacts. |
| 👥 Emergency contacts | Manage the trusted people notified during an emergency. |
| 📍 Location sharing & history | Record and review recent positions. |
| 🗂️ Emergency event tracking | Durable, auditable lifecycle: active → acknowledged → resolved. |
| 🤖 AI risk assessment | Score how risky a location/time is, with a versioned model. |
| 💡 Safety recommendations | Deterministic, explainable guidance from risk signals. |

## Architecture

SafeAI follows **Clean Architecture** — dependencies point inward, the domain is
framework-free, and infrastructure (DB, ML, notifications) is replaceable.

```
api/  →  application/  →  domain/  ←  infrastructure/      core/ (config·security·logging)
HTTP     use cases        entities    SQLAlchemy · ML ·     cross-cutting
         orchestration    & rules     notifiers (adapters)
```

- **`domain/`** — entities, value objects, and ports (interfaces). Pure Python.
- **`application/`** — use cases that orchestrate the domain via ports.
- **`infrastructure/`** — SQLAlchemy repositories, ML model, notifiers.
- **`api/`** — thin FastAPI controllers + request/response schemas.
- **`core/`** — configuration, security (hashing/JWT), logging.

Full detail, with workflow and security diagrams, in
[`docs/architecture.md`](docs/architecture.md).

## Technology stack

| Layer | Technology | Why ([rationale](docs/technology-decisions.md)) |
|-------|-----------|---------|
| Backend | **FastAPI**, Python 3.12 | Typed, async, auto-documented |
| Data | **PostgreSQL** (PostGIS-ready), **SQLAlchemy 2.x**, **Alembic** | Relational integrity, safe queries, versioned schema |
| Validation/config | **Pydantic v2** | One model for DTOs + fail-fast config |
| AI/ML | **scikit-learn**, pandas, numpy | Right fit for tabular, explainable risk scoring |
| Frontend | **Next.js**, **TypeScript**, **Tailwind CSS** | Typed, conventional, fast UI |
| Infra | **Docker**, Docker Compose | Reproducible local stack |
| CI | **GitHub Actions** | Lint · types · tests · build as a gate |
| Quality | **ruff**, **mypy**, **pytest** | Fast lint, enforced types, real tests |

## Documentation

| Document | Purpose |
|----------|---------|
| [architecture.md](docs/architecture.md) | System & Clean Architecture, workflows, security, scaling |
| [security-design.md](docs/security-design.md) | Threat model, abuse cases, privacy-by-design, controls (built vs planned) |
| [technology-decisions.md](docs/technology-decisions.md) | ADR-style rationale for every major choice |
| [database-design.md](docs/database-design.md) | Schema, constraints, indexing, scaling |
| [api-contract.md](docs/api-contract.md) | Endpoint request/response contract |
| [development-roadmap.md](docs/development-roadmap.md) | Phased delivery plan |
| [testing-strategy.md](docs/testing-strategy.md) | Test pyramid, coverage, CI gate |
| [glossary.md](docs/glossary.md) | Plain-language definitions of key concepts |

## Local setup

### Prerequisites

- Docker & Docker Compose (recommended path), **or**
- Python 3.12+ and Node.js 20+ for running services directly.

### Quick start (Docker)

```bash
cp .env.example .env          # fill in values; set a strong SAFEAI_JWT_SECRET_KEY
docker compose up --build     # starts PostgreSQL + the API
# → Liveness:   http://localhost:8000/api/v1/health/live
# → Readiness:  http://localhost:8000/api/v1/health/ready
# → API docs:   http://localhost:8000/docs
```

### Run services directly

**Backend** (defaults to local SQLite — no Postgres needed):

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload                        # http://localhost:8000/docs
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev                                           # http://localhost:3000
```

### Quality gate (run locally — same as CI)

```bash
# backend
cd backend && ruff check . && ruff format --check . && mypy app && pytest --cov
# frontend
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Development roadmap

| Phase | Focus | Status |
|------:|-------|--------|
| 1 | Engineering foundation (this milestone) | 🟡 In progress |
| 2 | Authentication & user management | ⬜ Planned |
| 3 | Emergency workflow (SOS, contacts, events) | ⬜ Planned |
| 4 | Location tracking | ⬜ Planned |
| 5 | AI risk prediction & recommendations | ⬜ Planned |
| 6 | Dashboard & deployment | ⬜ Planned |

Details in [`docs/development-roadmap.md`](docs/development-roadmap.md).

## Future enhancements

- **PostGIS** geospatial queries ("incidents near me", spatial risk).
- Real notification transports (SMS/push) behind the existing `Notifier` port.
- Asynchronous notification delivery via a queue + workers.
- Refresh-token rotation and rate limiting at the edge.
- Model improvements with richer features and offline evaluation gates.

## License

MIT — see `LICENSE` (to be added).

---

<div align="center">
<sub>Engineered with Clean Architecture, tested discipline, and reasoned decisions.</sub>
</div>
