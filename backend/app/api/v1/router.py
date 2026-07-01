"""Aggregate router for API v1.

Collects every v1 route module into a single ``APIRouter`` that the application
factory mounts under ``/api/v1``. New resource routers (auth, contacts,
emergency, location, risk) are registered here as later phases land.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes import auth, health, users

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(users.router)

# Future phases register their routers here, e.g.:
#   api_router.include_router(emergency.router, prefix="/emergency")
