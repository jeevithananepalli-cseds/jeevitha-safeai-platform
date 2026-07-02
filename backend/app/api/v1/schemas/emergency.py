"""Request/response schemas for contacts and emergency endpoints.

DTOs validate the wire contract at the boundary (see docs/api-contract.md).
Coordinate ranges and phone format are validated here; the domain re-validates
coordinates via the ``Coordinates`` value object as defense in depth.
"""

from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent

# E.164: a leading '+' then 7-15 digits, first digit non-zero.
_E164_PATTERN = r"^\+[1-9]\d{6,14}$"
_LAT = Field(ge=-90, le=90)
_LNG = Field(ge=-180, le=180)


class ContactCreateRequest(BaseModel):
    """Body of ``POST /contacts``."""

    contact_name: str = Field(min_length=1, max_length=120)
    phone_number: str = Field(pattern=_E164_PATTERN)
    relationship: str | None = Field(default=None, max_length=50)


class ContactResponse(BaseModel):
    """A returned emergency contact."""

    id: int
    contact_name: str
    phone_number: str
    relationship: str | None

    @classmethod
    def from_entity(cls, contact: EmergencyContact) -> ContactResponse:
        if contact.id is None:
            msg = "cannot serialize an unpersisted contact"
            raise ValueError(msg)
        return cls(
            id=contact.id,
            contact_name=contact.contact_name,
            phone_number=contact.phone_number,
            relationship=contact.relationship,
        )


class SosRequest(BaseModel):
    """Body of ``POST /emergency/sos``."""

    event_type: str = Field(default="sos", min_length=1, max_length=30)
    latitude: float = _LAT
    longitude: float = _LNG


class EventResponse(BaseModel):
    """A returned emergency event."""

    id: int
    event_type: str
    status: str
    latitude: float
    longitude: float
    created_at: dt.datetime

    @classmethod
    def from_entity(cls, event: EmergencyEvent) -> EventResponse:
        if event.id is None or event.created_at is None:
            msg = "cannot serialize an unpersisted event"
            raise ValueError(msg)
        return cls(
            id=event.id,
            event_type=event.event_type,
            status=event.status.value,
            latitude=event.location.latitude,
            longitude=event.location.longitude,
            created_at=event.created_at,
        )


class SosResponse(EventResponse):
    """The response to an SOS activation — an event plus how many were notified."""

    notified_contacts: int

    @classmethod
    def from_result(cls, event: EmergencyEvent, notified_contacts: int) -> SosResponse:
        base = EventResponse.from_entity(event)
        return cls(**base.model_dump(), notified_contacts=notified_contacts)
