"""Notifier interface (port) — emergency alert delivery.

The domain defines *that* contacts are notified; the transport (a structured log
today, SMS/push later) is an infrastructure adapter. Delivery is **best-effort
and independent per contact**: one failing recipient must not prevent the others
from being reached. Implementations return the number successfully notified.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent


class Notifier(Protocol):
    """Delivers an emergency alert to a set of contacts."""

    def notify(self, event: EmergencyEvent, contacts: list[EmergencyContact]) -> int:
        """Notify each contact about ``event``; return how many were reached."""
        ...
