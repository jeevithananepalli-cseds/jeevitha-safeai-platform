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
    placeholder_secret = Settings.model_fields["jwt_secret_key"].default
    insecure = Settings(environment="production", jwt_secret_key=placeholder_secret)
    with pytest.raises(RuntimeError, match="JWT_SECRET_KEY"):
        insecure.validate_runtime()

    # A real secret passes.
    secure = Settings(environment="production", jwt_secret_key="a-strong-unique-secret")
    secure.validate_runtime()  # must not raise


def test_access_token_expiry_must_be_positive() -> None:
    with pytest.raises(ValueError, match="access_token_expire_minutes"):
        Settings(access_token_expire_minutes=0)


def test_bcrypt_rounds_bounds_are_enforced() -> None:
    with pytest.raises(ValueError, match="bcrypt_rounds"):
        Settings(bcrypt_rounds=3)  # below bcrypt's practical floor
    with pytest.raises(ValueError, match="bcrypt_rounds"):
        Settings(bcrypt_rounds=32)  # above bcrypt's maximum


def test_production_requires_strong_bcrypt_cost() -> None:
    weak = Settings(
        environment="production",
        jwt_secret_key="a-strong-unique-secret",
        bcrypt_rounds=4,
    )
    with pytest.raises(RuntimeError, match="BCRYPT_ROUNDS"):
        weak.validate_runtime()

    strong = Settings(
        environment="production",
        jwt_secret_key="a-strong-unique-secret",
        bcrypt_rounds=12,
    )
    strong.validate_runtime()  # must not raise
