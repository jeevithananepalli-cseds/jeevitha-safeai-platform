"""Health endpoint response schemas.

Liveness and readiness are distinct concerns (see docs/architecture.md §9):

* **Liveness** — is the process up and serving? No dependencies are checked.
* **Readiness** — can the service do useful work (i.e. is the database
  reachable)? A failed readiness check returns ``503`` with ``success=false``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LivenessStatus(BaseModel):
    """Payload of ``GET /api/v1/health/live`` — process liveness only."""

    status: Literal["alive"]
    version: str


class ReadinessStatus(BaseModel):
    """Payload of a successful ``GET /api/v1/health/ready`` — dependencies OK."""

    status: Literal["ready"]
    version: str
    database: Literal["up"]
