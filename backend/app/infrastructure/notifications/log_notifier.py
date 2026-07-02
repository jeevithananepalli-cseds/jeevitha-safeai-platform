"""Structured-log implementation of the ``Notifier`` port.

The Phase 3 notification transport: it records an audit line per contact. This
is ideal for development and doubles as an audit trail; real transports (SMS via
Twilio/SNS, push via FCM/APNs) implement the same port later without touching
any use case. Delivery is **best-effort and independent per contact** — one
failing recipient does not stop the others.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.domain.entities.emergency_contact import EmergencyContact
from app.domain.entities.emergency_event import EmergencyEvent

logger = get_logger(__name__)


class LogNotifier:
    """Notify contacts by emitting a structured log entry for each."""

    def notify(self, event: EmergencyEvent, contacts: list[EmergencyContact]) -> int:
        notified = 0
        for contact in contacts:
            try:
                self._deliver(event, contact)
                notified += 1
            except Exception:
                # One failing recipient must not prevent the others being reached.
                logger.exception("Failed to notify contact_id=%s", contact.id)
        return notified

    def _deliver(self, event: EmergencyEvent, contact: EmergencyContact) -> None:
        """Deliver a single notification. Overridable by real transports."""
        logger.info(
            "SOS notification | event_id=%s status=%s -> contact_id=%s (%s)",
            event.id,
            event.status.value,
            contact.id,
            contact.relationship or "contact",
        )
