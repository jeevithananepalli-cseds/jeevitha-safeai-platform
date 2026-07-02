"""Location routes: record the current position and read location history."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import (
    CurrentUserId,
    GetLocationHistoryUseCaseDep,
    PaginationDep,
    RecordLocationUseCaseDep,
)
from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.location import LocationSampleResponse, LocationUpdateRequest
from app.application.use_cases.record_location import RecordLocationCommand
from app.domain.value_objects.coordinates import Coordinates

router = APIRouter(tags=["location"])


@router.post(
    "/location/update",
    response_model=ApiResponse[LocationSampleResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Record the authenticated user's current position",
)
def update_location(
    payload: LocationUpdateRequest,
    user_id: CurrentUserId,
    use_case: RecordLocationUseCaseDep,
) -> ApiResponse[LocationSampleResponse]:
    sample = use_case.execute(
        RecordLocationCommand(
            user_id=user_id,
            location=Coordinates(latitude=payload.latitude, longitude=payload.longitude),
        )
    )
    return ApiResponse.ok(LocationSampleResponse.from_entity(sample))


@router.get(
    "/location/history",
    response_model=ApiResponse[list[LocationSampleResponse]],
    summary="List the authenticated user's location history (newest first)",
)
def location_history(
    user_id: CurrentUserId,
    use_case: GetLocationHistoryUseCaseDep,
    pagination: PaginationDep,
) -> ApiResponse[list[LocationSampleResponse]]:
    page = use_case.execute(user_id, limit=pagination.limit, offset=pagination.offset)
    items = [LocationSampleResponse.from_entity(sample) for sample in page.items]
    return ApiResponse.paginated(
        items, total=page.total, page=pagination.page, limit=pagination.limit
    )
