"""Authentication: password hashing (stdlib PBKDF2) + JWT (PyJWT).

No native dependencies — uses hashlib/PyJWT only.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from collections import defaultdict, deque
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


# --- login throttling ------------------------------------------------------
# In-memory, per-process. Enough for a single-user desktop app: it stops casual
# brute force. A shared store would be required for a multi-worker deployment.
class LoginThrottle:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._attempts[key]
        cutoff = now - self.window_seconds
        while q and q[0] < cutoff:
            q.popleft()
        return q

    def retry_after(self, key: str) -> int:
        """Seconds until another attempt is allowed; 0 when not locked out."""
        now = time.time()
        with self._lock:
            q = self._prune(key, now)
            if len(q) < self.max_attempts:
                return 0
            return max(1, int(self.window_seconds - (now - q[0])))

    def record_failure(self, key: str) -> None:
        now = time.time()
        with self._lock:
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._attempts.pop(key, None)


login_throttle = LoginThrottle(settings.LOGIN_MAX_ATTEMPTS, settings.LOGIN_LOCKOUT_SECONDS)
