# ── SafeAI backend image ──────────────────────────────────────────────────
# Pinned to Python 3.12 (the project's target runtime) regardless of the host's
# local Python. Slim base keeps the image small; a non-root user runs the app.

FROM python:3.12-slim AS base

# Predictable, fast Python in containers.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first (layer cached until pyproject changes).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# Copy the application source.
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini ./

# Run as an unprivileged user.
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Container-level healthcheck hits the LIVENESS endpoint (no DB dependency), so a
# transient database outage does not cause the orchestrator to kill a healthy
# API. Readiness (DB-aware) is for the load balancer, not the liveness probe.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; \
sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health/live').status==200 else 1)"

# Apply database migrations, then serve. Running `alembic upgrade head` at
# startup makes `docker compose up` produce a fully working system on a fresh
# volume (idempotent: a no-op when the schema is already current).
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
