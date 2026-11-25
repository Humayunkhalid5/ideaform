"""JWT secret guard, rate limiter and token helpers (no database needed)."""

from __future__ import annotations

import pytest

from app.config import Settings, check_jwt_secret
from app.core.rate_limit import SlidingWindowLimiter
from app.core.security import create_access_token, decode_token, hash_password, verify_password


@pytest.mark.parametrize("secret", ["", "change-me-in-production", "short-secret"])
def test_jwt_guard_rejects_weak_secrets(secret):
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        check_jwt_secret(Settings(environment="production", jwt_secret=secret))


def test_jwt_guard_also_applies_in_development():
    with pytest.raises(RuntimeError):
        check_jwt_secret(Settings(environment="development", jwt_secret="change-me-in-production"))


def test_jwt_guard_accepts_strong_secret_and_test_env():
    check_jwt_secret(Settings(environment="production", jwt_secret="x" * 48))
    check_jwt_secret(Settings(environment="test", jwt_secret="change-me-in-production"))


def test_limiter_blocks_after_limit_and_recovers():
    limiter = SlidingWindowLimiter(attempts=3, window_seconds=60)
    assert all(limiter.hit("ip", now=t) is None for t in (0, 1, 2))
    wait = limiter.hit("ip", now=3)
    assert wait is not None and 56 < wait <= 57
    assert limiter.hit("other-ip", now=3) is None  # keys are independent
    assert limiter.hit("ip", now=61) is None  # first hit left the window


def test_password_hash_roundtrip():
    hashed = hash_password("password123")
    assert hashed != "password123"
    assert verify_password("password123", hashed)
    assert not verify_password("wrong", hashed)


def test_token_roundtrip():
    assert decode_token(create_access_token("abc")) == "abc"
