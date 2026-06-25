"""Application layer — use cases and orchestration.

Contains application-specific business rules: use cases that coordinate domain
entities and ports to fulfill a user intent (e.g. ``TriggerSosUseCase``).

Depends on ``domain`` only. It must not depend on ``api`` or on concrete
``infrastructure`` implementations — it talks to infrastructure exclusively
through the interfaces (ports) declared in ``domain``. Use cases are populated
from Phase 2 onward; this package establishes the boundary now.
"""
