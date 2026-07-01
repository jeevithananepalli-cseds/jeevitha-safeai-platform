"""Security adapters: concrete implementations of security-related ports.

Wraps the pure helpers in ``app.core.security`` behind the domain ports
(``PasswordHasher``) and provides a settings-bound JWT token service, keeping
configuration (the signing secret) out of the use cases.
"""
