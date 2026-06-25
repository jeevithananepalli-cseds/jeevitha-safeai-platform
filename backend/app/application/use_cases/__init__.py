"""Use cases — one class per user intent, orchestrating domain + ports.

Each use case (e.g. ``RegisterUserUseCase``, ``TriggerSosUseCase``) receives its
dependencies as domain interfaces (constructor injection) and contains no
framework code. Added per the development roadmap from Phase 2 onward.
"""
