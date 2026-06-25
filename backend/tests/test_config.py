"""Unit tests for application configuration."""

from __future__ import annotations

import pytest

from app.core.config import Settings


def test_defaults_are_sane() -> None:
    settings = Settings()
    assert settings.app_name == "SafeAI"
    assert settings.environment == "development"
    assert settings.access_token_expire_minutes > 0
    assert settings.is_production is False


def test_log_level_is_normalized_and_validated() -> None:
    assert Settings(log_level="debug").log_level == "DEBUG"

    with pytest.raises(ValueError, match="log_level"):
        Settings(log_level="verbose")


def test_cors_origins_are_parsed_into_a_list() -> None:
    settings = Settings(cors_origins="http://a.com, http://b.com ,")
    assert settings.cors_origin_list == ["http://a.com", "http://b.com"]


def test_production_requires_a_real_jwt_secret() -> None:
    # The placeholder secret must be rejected at runtime validation in prod.
    insecure = Settings(environment="production")
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        insecure.validate_runtime()

    # A real secret passes.
    secure = Settings(environment="production", jwt_secret_key="a-strong-unique-secret")
    secure.validate_runtime()  # must not raise


def test_access_token_expiry_must_be_positive() -> None:
    with pytest.raises(ValueError, match="access_token_expire_minutes"):
        Settings(access_token_expire_minutes=0)
