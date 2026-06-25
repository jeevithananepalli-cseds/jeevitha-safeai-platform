"""API layer — the HTTP interface (outermost circle).

FastAPI routers and pydantic request/response schemas (DTOs). Controllers here
are intentionally thin: validate input, invoke an application use case, and shape
the response envelope. They depend on ``application`` and ``domain`` and own the
dependency-injection wiring at the edge.
"""
