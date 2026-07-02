"""Emergency contact routes: add and list a user's trusted contacts."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import (
    AddContactUseCaseDep,
    CurrentUserId,
    ListContactsUseCaseDep,
    PaginationDep,
)
from app.api.v1.schemas.common import ApiResponse
from app.api.v1.schemas.emergency import ContactCreateRequest, ContactResponse
from app.application.use_cases.add_contact import AddContactCommand

router = APIRouter(tags=["contacts"])


@router.post(
    "/contacts",
    response_model=ApiResponse[ContactResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Add an emergency contact",
)
def add_contact(
    payload: ContactCreateRequest,
    user_id: CurrentUserId,
    use_case: AddContactUseCaseDep,
) -> ApiResponse[ContactResponse]:
    contact = use_case.execute(
        AddContactCommand(
            user_id=user_id,
            contact_name=payload.contact_name,
            phone_number=payload.phone_number,
            relationship=payload.relationship,
        )
    )
    return ApiResponse.ok(ContactResponse.from_entity(contact))


@router.get(
    "/contacts",
    response_model=ApiResponse[list[ContactResponse]],
    summary="List the authenticated user's emergency contacts",
)
def list_contacts(
    user_id: CurrentUserId,
    use_case: ListContactsUseCaseDep,
    pagination: PaginationDep,
) -> ApiResponse[list[ContactResponse]]:
    page = use_case.execute(user_id, limit=pagination.limit, offset=pagination.offset)
    items = [ContactResponse.from_entity(contact) for contact in page.items]
    return ApiResponse.paginated(
        items, total=page.total, page=pagination.page, limit=pagination.limit
    )
