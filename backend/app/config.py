"""Application configuration loaded from environment variables.

All sensitive values (JWT secret, DB URL, model path) are read from the
environment so the same image runs locally, in Docker Compose, or packaged
via Tauri without code changes.
"""
from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

_PLACEHOLDER_SECRETS = {"", "change-me-in-production", "changeme", "secret"}


def _split_origins(raw: str) -> list[str]:
    """Parse CORS origins.

    ``*`` is rejected on purpose: the app sends ``Authorization: Bearer`` and
    FastAPI would have to combine it with credentials, which browsers refuse.
    Use an explicit list (Vite dev server + Tauri webview) instead.
    """
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    if not origins:
        return []
    if "*" in origins:
        raise ValueError(
            "CORS_ORIGINS='*' nie je podporované (Bearer token + credentials). "
            "Zadaj explicitný zoznam, napr. "
            "CORS_ORIGINS=http://localhost:1420,http://127.0.0.1:1420"
        )
    return origins


class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    # Data layer (MVP default: SQLite; switch to Postgres via DATABASE_URL).
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./app.db")

    # Background jobs.
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # LLM runtime.
    LLM_MODEL_PATH: str = os.getenv("LLM_MODEL_PATH", "")
    LLM_GPU_LAYERS: int = int(os.getenv("LLM_GPU_LAYERS", "-1"))  # -1 = auto to GPU
    LLM_DEFAULT_HINT: str = os.getenv("LLM_DEFAULT_HINT", "7b")

    # Auth — the secret must be provided explicitly outside development.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Login throttling (per username + client IP).
    LOGIN_MAX_ATTEMPTS: int = int(os.getenv("LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_SECONDS: int = int(os.getenv("LOGIN_LOCKOUT_SECONDS", "300"))

    # CORS — explicit origins only, see _split_origins().
    CORS_ORIGINS: list[str] = _split_origins(
        os.getenv("CORS_ORIGINS", "http://localhost:1420,http://127.0.0.1:1420")
    )

    # Local encrypted-at-rest store (Sprint 1).
    ENCRYPTION_KEY_FILE: str = os.getenv("ENCRYPTION_KEY_FILE", "./.enc_key")


settings = Settings()

# Outside development an unset/placeholder JWT secret must never reach production:
# every token would be forgeable. Fail fast at import time instead.
if settings.APP_ENV.lower() not in {"development", "dev", "test", "local"}:
    if settings.JWT_SECRET.strip().lower() in _PLACEHOLDER_SECRETS:
        raise RuntimeError(
            "JWT_SECRET musí byť nastavený na silnú hodnotu, keď APP_ENV="
            f"{settings.APP_ENV!r}. Vygeneruj ju napr. `python -c "
            "'import secrets;print(secrets.token_urlsafe(48))'`."
        )
if not settings.JWT_SECRET.strip():
    # Development convenience: ephemeral secret, invalidates tokens on restart.
    settings.JWT_SECRET = secrets.token_urlsafe(48)
