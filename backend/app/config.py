"""Application configuration loaded from environment variables.

All sensitive values (JWT secret, DB URL, model path) are read from the
environment so the same image runs locally, in Docker Compose, or packaged
via Tauri without code changes.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


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

    # Auth (Sprint 1) — placeholder so imports are stable.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # CORS.
    CORS_ORIGINS: list[str] = os.getenv("CORS_ORIGINS", "*").split(",")

    # Local encrypted-at-rest store (Sprint 1).
    ENCRYPTION_KEY_FILE: str = os.getenv("ENCRYPTION_KEY_FILE", "./.enc_key")


settings = Settings()
