"""Unit tests for the register and authenticate use cases.

These use in-memory fakes only — no database, no HTTP, no bcrypt — proving the
application layer depends purely on the domain ports.
"""

from __future__ import annotations

import pytest

from app.application.use_cases.authenticate_user import (
    AuthenticateUserCommand,
    AuthenticateUserUseCase,
)
from app.application.use_cases.register_user import RegisterUserCommand, RegisterUserUseCase
from app.domain.exceptions import EmailAlreadyExistsError, InvalidCredentialsError
from tests.fakes import FakeHasher, InMemoryUserRepository


def _register(users: InMemoryUserRepository, email: str = "jeevitha@example.com") -> None:
    RegisterUserUseCase(users, FakeHasher()).execute(
        RegisterUserCommand(name="Jeevitha", email=email, password="a-good-password")
    )


# --- register -----------------------------------------------------------------


def test_register_persists_user_with_hashed_password() -> None:
    users = InMemoryUserRepository()
    use_case = RegisterUserUseCase(users, FakeHasher())

    user = use_case.execute(
        RegisterUserCommand(name="Jeevitha", email="Jeevitha@Example.com", password="secret-pass")
    )

    assert user.id is not None
    assert user.created_at is not None
    assert user.password_hash == "hashed::secret-pass"
    assert user.password_hash != "secret-pass"  # never plaintext


def test_register_normalizes_email() -> None:
    users = InMemoryUserRepository()
    RegisterUserUseCase(users, FakeHasher()).execute(
        RegisterUserCommand(name="J", email="  Mixed@CASE.com ", password="secret-pass")
    )
    assert users.get_by_email("mixed@case.com") is not None


def test_register_rejects_duplicate_email() -> None:
    users = InMemoryUserRepository()
    _register(users)
    with pytest.raises(EmailAlreadyExistsError):
        _register(users)


def test_register_rejects_duplicate_email_case_insensitively() -> None:
    users = InMemoryUserRepository()
    _register(users, email="dup@example.com")
    with pytest.raises(EmailAlreadyExistsError):
        _register(users, email="DUP@example.com")


# --- authenticate -------------------------------------------------------------


def test_authenticate_succeeds_with_correct_credentials() -> None:
    users = InMemoryUserRepository()
    _register(users)

    user = AuthenticateUserUseCase(users, FakeHasher()).execute(
        AuthenticateUserCommand(email="jeevitha@example.com", password="a-good-password")
    )
    assert user.email == "jeevitha@example.com"


def test_authenticate_rejects_wrong_password() -> None:
    users = InMemoryUserRepository()
    _register(users)
    with pytest.raises(InvalidCredentialsError):
        AuthenticateUserUseCase(users, FakeHasher()).execute(
            AuthenticateUserCommand(email="jeevitha@example.com", password="wrong")
        )


def test_authenticate_rejects_unknown_email_with_same_error() -> None:
    users = InMemoryUserRepository()
    # No user registered; must raise the SAME error as a wrong password
    # (no account enumeration).
    with pytest.raises(InvalidCredentialsError):
        AuthenticateUserUseCase(users, FakeHasher()).execute(
            AuthenticateUserCommand(email="nobody@example.com", password="whatever")
        )
