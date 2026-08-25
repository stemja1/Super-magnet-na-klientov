"""Authentication: password hashing (stdlib PBKDF2) + JWT (PyJWT).

No native dependencies — uses hashlib/PyJWT only.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings

PBKDF2_ITERS = 100_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERS)
    return f"pbkdf2_sha256${PBKDF2_ITERS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_s, salt_hex, dk_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        expected = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), iters
        )
        return hmac.compare_digest(expected.hex(), dk_hex)
    except Exception:
        return False


def create_access_token(sub: str, role: str, expires_min: int | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(
        minutes=expires_min or settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": str(sub), "role": role, "exp": exp}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
