"""Typed application configuration.

Configuration is loaded from environment variables (and an optional ``.env``
file) via ``pydantic-settings``. Centralizing settings in one typed object means:

* every consumer gets validated, typed values (no scattered ``os.getenv``);
* required secrets are validated **at startup** — the app fails fast rather than
  surfacing a misconfiguration deep in a request;
* tests can construct ``Settings`` with explicit overrides.

All variables are namespaced with the ``SAFEAI_`` prefix to avoid collisions.
See ``.env.example`` for the full set.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["development", "staging", "production"]

# Placeholder shipped in .env.example; rejected in production so a real secret
# must be provided.
_INSECURE_SECRET_SENTINEL = "change-me-in-production-use-a-48-byte-random-string"


class Settings(BaseSettings):
    """Validated, environment-driven application settings."""

    model_config = SettingsConfigDict(
        env_prefix="SAFEAI_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "SafeAI"
    version: str = "0.1.0"
    environment: Environment = "development"
    log_level: str = "INFO"

    # --- Security (JWT) ---
    jwt_secret_key: str = Field(default=_INSECURE_SECRET_SENTINEL, min_length=1)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=60, gt=0)

    # --- Database ---
    # Default targets a local SQLite file so the app and its smoke tests can run
    # with zero external services; production/compose overrides this with a
    # PostgreSQL URL. See docs/technology-decisions.md.
    database_url: str = "sqlite:///./safeai.db"

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    @property
    def is_production(self) -> bool:
        """True when running in the production environment."""
        return self.environment == "production"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins parsed from the comma-separated env value."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @field_validator("log_level")
    @classmethod
    def _validate_log_level(cls, value: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = value.upper()
        if upper not in allowed:
            msg = f"log_level must be one of {sorted(allowed)}, got {value!r}"
            raise ValueError(msg)
        return upper

    def validate_runtime(self) -> None:
        """Enforce invariants that depend on the environment.

        Called once at application startup. Kept separate from field validators
        so unit tests can build a ``Settings`` object freely without tripping
        production-only rules.
        """
        if self.is_production and self.jwt_secret_key == _INSECURE_SECRET_SENTINEL:
            msg = (
                "SAFEAI_JWT_SECRET_KEY must be set to a strong, unique value in "
                "production; the placeholder default is not permitted."
            )
            raise RuntimeError(msg)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached ``Settings`` instance.

    Cached so the environment is parsed once per process. Tests that need
    different values can call ``get_settings.cache_clear()`` or construct
    ``Settings(...)`` directly.
    """
    return Settings()
