"""Infrastructure layer — adapters to the outside world.

Concrete implementations of domain ports: the SQLAlchemy database, repository
implementations, the ML risk model, and notification transports. This is where
framework- and vendor-specific code lives.

Depends inward on ``domain`` (whose interfaces it implements) and on ``core``.
It must not depend on ``api``. Swapping an adapter here (e.g. a log notifier for
an SMS notifier) leaves the inner layers untouched.
"""
