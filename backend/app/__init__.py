"""SafeAI backend application package.

A FastAPI service organized with Clean Architecture: ``domain`` (framework-free
business rules) at the center, wrapped by ``application`` (use cases),
``infrastructure`` (adapters), and ``api`` (HTTP). ``core`` holds cross-cutting
concerns (config, security, logging). See ``docs/architecture.md``.
"""

__version__ = "0.1.0"
