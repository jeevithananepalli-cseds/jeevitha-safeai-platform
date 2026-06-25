"""Request/response schemas (DTOs) for the v1 API.

These pydantic models define the wire contract and validate all inbound data at
the system boundary. They are distinct from domain entities and ORM models — the
API speaks DTOs and never leaks internal representations.
"""
