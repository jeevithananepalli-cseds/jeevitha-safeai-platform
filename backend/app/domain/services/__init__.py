"""Domain service ports — interfaces for capabilities the domain depends on.

Ports such as ``Notifier`` (alert delivery) and ``RiskAssessor`` (risk scoring)
are declared here and implemented by adapters in ``app.infrastructure``. Keeping
these as interfaces lets the notification transport or ML backend change without
touching use cases. See docs/architecture.md sections 5 and 6.
"""
