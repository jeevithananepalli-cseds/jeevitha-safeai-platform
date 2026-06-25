"""Notification adapters implementing the ``Notifier`` port.

Phase 3 ships a ``LogNotifier`` (structured-log delivery, ideal for dev and as an
audit trail). Real transports (SMS via Twilio/SNS, push via FCM/APNs) slot in
here later without changing any use case. See docs/architecture.md §5.
"""
