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


class DuplicateContactError(DomainError):
    """Raised when adding an emergency contact whose phone number already
    exists for the same user."""


class EventNotFoundError(DomainError):
    """Raised when an emergency event does not exist *for the requesting user*.

    Not-owned events are reported as not-found (rather than forbidden) so an
    attacker cannot enumerate which event ids exist — important for a safety
    product (see docs/security-design.md)."""


class InvalidStatusTransitionError(DomainError):
    """Raised when an emergency event's status change is not permitted by its
    lifecycle (e.g. resolving then re-activating)."""


class EventConflictError(DomainError):
    """Raised when persisting an event violates the per-user idempotency
    constraint — i.e. a concurrent request already created it. The SOS use case
    recovers by returning the existing event (idempotent replay)."""
