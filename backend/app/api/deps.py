"""FastAPI dependency providers — the composition root.

These functions resolve per-request dependencies (settings, database, session,
repositories, use cases, and the current user) from objects the application
factory placed on ``app.state``. Keeping the wiring here (the outer ``api``
layer) means inner layers never reach for globals, and tests can override any
provider via ``app.dependency_overrides``.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.pagination import Pagination, pagination_params
from app.application.use_cases.authenticate_user import AuthenticateUserUseCase
from app.application.use_cases.register_user import RegisterUserUseCase
from app.core.config import Settings
from app.core.security import InvalidTokenError
from app.domain.entities.user import User
from app.domain.repositories.user_repository import UserRepository
from app.domain.services.password_hasher import PasswordHasher
from app.infrastructure.db.repositories.user_repository import SqlAlchemyUserRepository
from app.infrastructure.db.session import Database
from app.infrastructure.security.bcrypt_hasher import BcryptPasswordHasher
from app.infrastructure.security.token_service import JwtTokenService

# Bearer scheme with auto_error disabled so we can return a consistent 401
# (rather than the library's default 403) when the header is missing.
_bearer_scheme = HTTPBearer(auto_error=False)


# --- infrastructure providers -------------------------------------------------


def get_app_settings(request: Request) -> Settings:
    """Return the settings the running app was configured with."""
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    """Return the app's :class:`Database` (engine + session factory)."""
    database: Database = request.app.state.database
    return database


def get_session(database: Database = Depends(get_database)) -> Iterator[Session]:
    """Yield a request-scoped session that is the unit of work.

    Commits on success and rolls back on any error, so use cases and
    repositories never manage transactions themselves. The session is always
    closed.
    """
    session = database.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_user_repository(session: Session = Depends(get_session)) -> UserRepository:
    """Provide the SQLAlchemy-backed user repository."""
    return SqlAlchemyUserRepository(session)


def get_password_hasher() -> PasswordHasher:
    """Provide the bcrypt password hasher."""
    return BcryptPasswordHasher()


def get_token_service(settings: Settings = Depends(get_app_settings)) -> JwtTokenService:
    """Provide the settings-bound JWT token service."""
    return JwtTokenService(settings)


# --- use-case providers -------------------------------------------------------


def get_register_user_use_case(
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> RegisterUserUseCase:
    return RegisterUserUseCase(users, hasher)


def get_authenticate_user_use_case(
    users: UserRepository = Depends(get_user_repository),
    hasher: PasswordHasher = Depends(get_password_hasher),
) -> AuthenticateUserUseCase:
    return AuthenticateUserUseCase(users, hasher)


# --- authentication -----------------------------------------------------------


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token_service: JwtTokenService = Depends(get_token_service),
    users: UserRepository = Depends(get_user_repository),
) -> User:
    """Resolve the authenticated user from the bearer token.

    Raises ``401`` for a missing, malformed, or expired token, or when the token
    refers to a user that no longer exists.
    """
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized

    try:
        token_data = token_service.decode(credentials.credentials)
        user_id = int(token_data.subject)
    except (InvalidTokenError, ValueError):
        raise unauthorized from None

    user = users.get_by_id(user_id)
    if user is None:
        raise unauthorized
    return user


# --- typed dependency aliases -------------------------------------------------
# Concise, reusable annotations for route signatures (modern FastAPI style).
# Every protected/paginated endpoint in later phases uses these.

SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]
SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_user)]
TokenServiceDep = Annotated[JwtTokenService, Depends(get_token_service)]
RegisterUserUseCaseDep = Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)]
AuthenticateUserUseCaseDep = Annotated[
    AuthenticateUserUseCase, Depends(get_authenticate_user_use_case)
]
PaginationDep = Annotated[Pagination, Depends(pagination_params)]
