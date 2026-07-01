"""Domain exceptions — business-rule violations, framework-independent.

These express *what* went wrong in domain terms (an email is taken, credentials
are invalid). Outer layers (the API) translate them into transport concerns
(HTTP status codes) via the global exception handlers, so use cases never import
FastAPI to signal an error.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for all domain-level errors."""


class EmailAlreadyExistsError(DomainError):
    """Raised when registering an email that already has an account."""


class InvalidCredentialsError(DomainError):
    """Raised when authentication fails (wrong email or password).

    Deliberately does not distinguish "unknown email" from "wrong password" so
    the caller cannot use it to enumerate registered accounts.
    """


class UserNotFoundError(DomainError):
    """Raised when a referenced user does not exist."""
