"""SQLAlchemy ORM models.

Each model maps a domain concept to a database table and inherits from
:class:`app.infrastructure.db.base.Base`. Importing this package registers every
model on ``Base.metadata`` for Alembic autogeneration.

Empty in Phase 1; tables are introduced per the development roadmap (users in
Phase 2, emergency tables in Phase 3, and so on).
"""
