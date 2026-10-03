"""Configuration guards: JWT secret and CORS origin parsing."""
import importlib
import os

import pytest

import app.config as config_module


def _reload(monkeypatch, **env):
    for key, value in env.items():
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)
    return importlib.reload(config_module)


def test_production_requires_strong_jwt_secret(monkeypatch):
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _reload(
            monkeypatch,
            APP_ENV="production",
            JWT_SECRET="change-me-in-production",
        )


def test_production_rejects_empty_jwt_secret(monkeypatch):
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        _reload(monkeypatch, APP_ENV="production", JWT_SECRET="")


def test_production_accepts_strong_secret(monkeypatch):
    mod = _reload(monkeypatch, APP_ENV="production", JWT_SECRET="a-real-long-random-secret")
    assert mod.settings.JWT_SECRET == "a-real-long-random-secret"


def test_development_generates_ephemeral_secret(monkeypatch):
    mod = _reload(monkeypatch, APP_ENV="development", JWT_SECRET="")
    assert len(mod.settings.JWT_SECRET) >= 32
    assert mod.settings.JWT_SECRET != ""


def test_cors_rejects_wildcard(monkeypatch):
    with pytest.raises(ValueError, match="CORS_ORIGINS"):
        _reload(monkeypatch, APP_ENV="test", JWT_SECRET="x", CORS_ORIGINS="*")


def test_cors_parses_explicit_list(monkeypatch):
    mod = _reload(
        monkeypatch,
        APP_ENV="test",
        JWT_SECRET="x",
        CORS_ORIGINS="http://localhost:1420, http://127.0.0.1:1420",
    )
    assert mod.settings.CORS_ORIGINS == [
        "http://localhost:1420",
        "http://127.0.0.1:1420",
    ]


def test_cors_default_is_localhost_only(monkeypatch):
    mod = _reload(monkeypatch, APP_ENV="test", JWT_SECRET="x", CORS_ORIGINS=None)
    assert "*" not in mod.settings.CORS_ORIGINS
    assert all(o.startswith("http://localhost") or o.startswith("http://127.0.0.1")
               for o in mod.settings.CORS_ORIGINS)


def test_login_throttle_lockout_and_reset():
    from app.services.auth import LoginThrottle

    t = LoginThrottle(max_attempts=3, window_seconds=60)
    assert t.retry_after("k") == 0
    for _ in range(3):
        t.record_failure("k")
    assert t.retry_after("k") > 0
    t.reset("k")
    assert t.retry_after("k") == 0


def test_login_throttle_is_per_key():
    from app.services.auth import LoginThrottle

    t = LoginThrottle(max_attempts=2, window_seconds=60)
    t.record_failure("a")
    t.record_failure("a")
    assert t.retry_after("a") > 0
    assert t.retry_after("b") == 0


def test_password_hash_roundtrip():
    from app.services.auth import hash_password, verify_password

    stored = hash_password("heslo123")
    assert stored.startswith("pbkdf2_sha256$")
    assert verify_password("heslo123", stored)
    assert not verify_password("zle", stored)


def test_password_hashes_are_salted():
    from app.services.auth import hash_password

    assert hash_password("heslo123") != hash_password("heslo123")
