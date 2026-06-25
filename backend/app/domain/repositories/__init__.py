"""Repository interfaces (ports) — defined by the domain, implemented outside.

These ``Protocol``/ABC interfaces (e.g. ``UserRepository``, ``EventRepository``)
declare *what* persistence the domain needs without dictating *how*. Concrete
implementations live in ``app.infrastructure.db.repositories``. This inversion is
what lets the domain stay framework-free and the data layer stay swappable.
"""
