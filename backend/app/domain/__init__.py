"""Domain layer — the innermost circle of the architecture.

Contains enterprise business rules: entities, value objects, and the
**interfaces** (ports) that outer layers implement. This package is deliberately
**framework-free**: it must not import FastAPI, SQLAlchemy, pydantic, or any
infrastructure. That isolation is what makes the business rules testable and the
surrounding technology replaceable.

The Dependency Rule: nothing in here may import from ``application``, ``api``,
``infrastructure``, or ``core`` (beyond the standard library).
"""
