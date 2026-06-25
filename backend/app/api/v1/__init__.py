"""Version 1 of the SafeAI HTTP API (mounted under ``/api/v1``).

Versioning the API under a path prefix lets us evolve the contract without
breaking existing clients: breaking changes ship as ``/api/v2``.
"""
