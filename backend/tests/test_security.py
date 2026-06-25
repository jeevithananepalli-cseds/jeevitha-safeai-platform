"""Unit tests for security utilities (password hashing + JWT)."""

from __future__ import annotations

import datetime as dt

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# At least 32 bytes, satisfying HS256's recommended minimum key length.
SECRET = "unit-test-secret-key-0123456789-abcdef"


# --- password hashing ---------------------------------------------------------


def test_hash_is_not_plaintext_and_is_salted() -> None:
    password = "S0me-Strong-Pass"
    hashed = hash_password(password)

    assert hashed != password
    # bcrypt salts each hash, so the same password hashes differently each time.
    assert hash_password(password) != hashed


def test_verify_password_accepts_correct_and_rejects_wrong() -> None:
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed) is True
    assert verify_password("wrong password", hashed) is False


def test_verify_password_is_safe_on_garbage_hash() -> None:
    # Must return False, never raise, on a malformed stored hash.
    assert verify_password("anything", "not-a-bcrypt-hash") is False


def test_hash_password_rejects_overlong_input() -> None:
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password("x" * 73)


# --- JWT ----------------------------------------------------------------------


def test_token_round_trip_preserves_subject() -> None:
    token = create_access_token("user-123", SECRET)
    data = decode_access_token(token, SECRET)

    assert data.subject == "user-123"
    assert data.expires_at > dt.datetime.now(tz=dt.UTC)


def test_decode_rejects_bad_signature() -> None:
    token = create_access_token("user-123", SECRET)
    with pytest.raises(InvalidTokenError):
        decode_access_token(token, "a-different-secret-key-0123456789-xyz")


def test_decode_rejects_expired_token() -> None:
    past = dt.datetime.now(tz=dt.UTC) - dt.timedelta(hours=2)
    token = create_access_token("user-123", SECRET, expires_minutes=60, now=past)

    with pytest.raises(InvalidTokenError):
        decode_access_token(token, SECRET)


def test_decode_rejects_malformed_token() -> None:
    with pytest.raises(InvalidTokenError):
        decode_access_token("not.a.jwt", SECRET)
