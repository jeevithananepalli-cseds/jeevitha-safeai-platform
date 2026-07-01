"""User routes: the authenticated user's profile."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.api.v1.schemas.auth import UserResponse
from app.api.v1.schemas.common import ApiResponse

router = APIRouter(tags=["users"])


@router.get(
    "/profile",
    response_model=ApiResponse[UserResponse],
    summary="Get the authenticated user's profile",
)
def get_profile(current_user: CurrentUser) -> ApiResponse[UserResponse]:
    """Return the profile of the user identified by the bearer token."""
    return ApiResponse.ok(UserResponse.from_entity(current_user))
