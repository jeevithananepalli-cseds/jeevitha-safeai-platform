"""Emergency routes: SOS activation and event retrieval."""

from __future__ import annotations

from fastapi import APIRouter, Header, Response, status

from app.api.deps import (
    CurrentUserId,
    GetEventUseCaseDep,
    TriggerSosUseCaseDep,
    UpdateEventStatusUseCaseDep,
)
from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.emergency import (
    EventResponse,
    EventStatusUpdateRequest,
    SosRequest,
    SosResponse,
)
from app.application.use_cases.trigger_sos import TriggerSosCommand
from app.domain.value_objects.coordinates import Coordinates

router = APIRouter(tags=["emergency"])


@router.post(
    "/emergency/sos",
    response_model=ApiResponse[SosResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Activate an SOS (idempotent via the Idempotency-Key header)",
)
def trigger_sos(
    payload: SosRequest,
    user_id: CurrentUserId,
    use_case: TriggerSosUseCaseDep,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ApiResponse[SosResponse]:
    result = use_case.execute(
        TriggerSosCommand(
            user_id=user_id,
            event_type=payload.event_type,
            location=Coordinates(latitude=payload.latitude, longitude=payload.longitude),
            idempotency_key=idempotency_key,
        )
    )
    # A replay of a prior Idempotency-Key returns the existing event with 200.
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return ApiResponse.ok(SosResponse.from_result(result.event, result.notified_contacts))


@router.get(
    "/emergency/{event_id}",
    response_model=ApiResponse[EventResponse],
    summary="Get one of the authenticated user's emergency events",
)
def get_event(
    event_id: int,
    user_id: CurrentUserId,
    use_case: GetEventUseCaseDep,
) -> ApiResponse[EventResponse]:
    event = use_case.execute(user_id, event_id)
    return ApiResponse.ok(EventResponse.from_entity(event))


@router.patch(
    "/emergency/{event_id}/status",
    response_model=ApiResponse[EventResponse],
    summary="Transition an emergency event's status (acknowledge, resolve, cancel)",
)
def update_event_status(
    event_id: int,
    payload: EventStatusUpdateRequest,
    user_id: CurrentUserId,
    use_case: UpdateEventStatusUseCaseDep,
) -> ApiResponse[EventResponse]:
    """Advance the event through its lifecycle.

    Transition rules are enforced by the domain: terminal states (resolved,
    cancelled) cannot be reopened — violations return ``409``.
    """
    event = use_case.execute(user_id=user_id, event_id=event_id, new_status=payload.status)
    return ApiResponse.ok(EventResponse.from_entity(event))
