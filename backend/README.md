# SafeAI — Backend

FastAPI service implementing the SafeAI platform with Clean Architecture.
See the top-level [`README.md`](../README.md) and [`docs/`](../docs) for the full
picture (architecture, API contract, roadmap).

## Layout

```
app/
  domain/          # entities, value objects, ports — framework-free
  application/     # use cases (orchestration)
  infrastructure/  # SQLAlchemy, ML, notifiers (adapters)
  api/             # FastAPI routers + request/response schemas
  core/            # config, security, logging
alembic/           # database migrations
tests/             # unit + API tests
```

The **Dependency Rule** is enforced by convention: inner layers never import
outer ones. See [`../docs/architecture.md`](../docs/architecture.md).

## Local development

```bash
# from backend/
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# run the API (defaults to local SQLite — no Postgres needed)
uvicorn app.main:app --reload
# → http://localhost:8000/docs                    (Swagger UI)
# → http://localhost:8000/api/v1/health/live       (liveness)
# → http://localhost:8000/api/v1/health/ready      (readiness, checks the DB)
```

To run against PostgreSQL, set `SAFEAI_DATABASE_URL` (see `../.env.example`) or
use Docker Compose from the repo root (`docker compose up`).

## Quality gate

```bash
ruff check .          # lint
ruff format --check . # format check
mypy app              # static types
pytest                # tests
pytest --cov          # tests + coverage (target ≥ 80%)
```

## Migrations (Alembic)

```bash
alembic revision --autogenerate -m "create users"   # generate
alembic upgrade head                                  # apply
```

The database URL is injected from settings (env), not stored in `alembic.ini`.

## Configuration

All settings are environment variables prefixed `SAFEAI_` (see
[`../.env.example`](../.env.example)), loaded and validated by
`app/core/config.py`. The app fails fast in production if the JWT secret is unset.
