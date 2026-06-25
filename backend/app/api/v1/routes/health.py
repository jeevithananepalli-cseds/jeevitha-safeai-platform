"""Health endpoints: liveness and readiness.

Two distinct probes (see docs/architecture.md §9):

* ``GET /api/v1/health/live`` — **liveness**. No dependency checks; returns
  ``200`` whenever the process is serving. This is what the container
  healthcheck targets, so a transient database outage does not cause the
  orchestrator to kill an otherwise-healthy API.
* ``GET /api/v1/health/ready`` — **readiness**. Verifies the database is
  reachable; returns ``200`` when ready and ``503`` with ``success=false`` when
  not, so a load balancer can route around a not-ready instance. ``/health`` is
  kept as a backward-compatible alias of the readiness probe.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import get_app_settings, get_database
from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.health import LivenessStatus, ReadinessStatus
from app.core.config import Settings
from app.infrastructure.db.session import Database

router = APIRouter(tags=["health"])


@router.get(
    "/health/live",
    response_model=ApiResponse[LivenessStatus],
    summary="Liveness probe (no dependencies)",
)
def liveness(
    settings: Settings = Depends(get_app_settings),
) -> ApiResponse[LivenessStatus]:
    """Report that the process is alive. Always ``200`` while serving."""
    return ApiResponse.ok(LivenessStatus(status="alive", version=settings.version))


@router.get(
    "/health/ready",
    response_model=ApiResponse[ReadinessStatus],
    summary="Readiness probe (checks the database)",
)
@router.get(
    "/health",
    response_model=ApiResponse[ReadinessStatus],
    include_in_schema=False,
    summary="Readiness probe (backward-compatible alias)",
)
def readiness(
    response: Response,
    settings: Settings = Depends(get_app_settings),
    database: Database = Depends(get_database),
) -> ApiResponse[ReadinessStatus]:
    """Report readiness, including database connectivity.

    Returns ``200`` with ``success=true`` when the database answers, and ``503``
    with ``success=false`` when it does not — keeping the envelope's ``success``
    flag consistent with the HTTP status code.
    """
    if database.ping():
        return ApiResponse.ok(
            ReadinessStatus(status="ready", version=settings.version, database="up")
        )

    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ApiResponse.fail(
        "service_unavailable",
        "Database is not reachable.",
        {"database": "down"},
    )
