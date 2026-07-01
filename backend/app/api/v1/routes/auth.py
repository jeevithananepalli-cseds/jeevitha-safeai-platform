"""Authentication routes: register and login.

Thin controllers — validate the request DTO, invoke a use case, and shape the
response envelope. Domain failures (duplicate email, invalid credentials) are
raised by the use cases and translated to HTTP by the global exception handlers,
so there is no error branching here.
"""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import AuthenticateUserUseCaseDep, RegisterUserUseCaseDep, TokenServiceDep
from app.api.v1.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.api.v1.schemas.common import ApiResponse
from app.application.use_cases.authenticate_user import AuthenticateUserCommand
from app.application.use_cases.register_user import RegisterUserCommand

router = APIRouter(tags=["auth"])


@router.post(
    "/register",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new account",
)
def register(
    payload: RegisterRequest,
    use_case: RegisterUserUseCaseDep,
) -> ApiResponse[UserResponse]:
    user = use_case.execute(
        RegisterUserCommand(name=payload.name, email=payload.email, password=payload.password)
    )
    return ApiResponse.ok(UserResponse.from_entity(user))


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Log in and receive an access token",
)
def login(
    payload: LoginRequest,
    use_case: AuthenticateUserUseCaseDep,
    token_service: TokenServiceDep,
) -> ApiResponse[TokenResponse]:
    user = use_case.execute(AuthenticateUserCommand(email=payload.email, password=payload.password))
    # user.id is guaranteed non-None for a persisted, authenticated user.
    issued = token_service.issue(str(user.id))
    return ApiResponse.ok(
        TokenResponse(access_token=issued.access_token, expires_in=issued.expires_in)
    )
