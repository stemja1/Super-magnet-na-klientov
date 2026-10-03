"""Minimal Google OAuth 2.0 client using only the standard library.

No google-* SDK dependency: token exchange and API calls go through urllib.
In sandbox mode (no client credentials) connectors simulate calls so the whole
pipeline is runnable offline / in CI.

The ``state`` parameter is generated per authorization request and verified on
callback (CSRF protection). Tokens are stored in a local file that is created
with owner-only permissions where the platform supports it.
"""
from __future__ import annotations

import hmac
import json
import logging
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger("google_oauth")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
STATE_TTL_SECONDS = 600


@dataclass
class GoogleTokens:
    access_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0
    scopes: str = ""


class GoogleOAuthClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: str,
        token_path: Optional[str] = None,
    ) -> None:
        self.client_id = client_id or ""
        self.client_secret = client_secret or ""
        self.redirect_uri = redirect_uri or ""
        self.scopes = scopes
        self.token_path = token_path or os.getenv("GOOGLE_TOKEN_PATH", ".google_tokens.json")
        self.tokens = self._load()
        self._pending_states: Dict[str, float] = {}
        self._lock = threading.Lock()

    # ---- config ----
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)

    def mode(self) -> str:
        return "live" if (self.is_configured() and self.tokens.access_token) else "sandbox"

    # ---- OAuth flow ----
    def get_auth_url(self, state: Optional[str] = None) -> tuple[str, str]:
        state = state or secrets.token_urlsafe(16)
        now = time.time()
        with self._lock:
            self._pending_states = {
                s: ts for s, ts in self._pending_states.items()
                if now - ts < STATE_TTL_SECONDS
            }
            self._pending_states[state] = now
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": self.scopes,
            "access_type": "offline",
            "prompt": "consent",
            "state": state,
        }
        return GOOGLE_AUTH_ENDPOINT + "?" + urllib.parse.urlencode(params), state

    def consume_state(self, state: str) -> bool:
        """Validate a callback ``state`` exactly once, then discard it.

        Comparing with hmac.compare_digest keeps the check constant-time; states
        expire so a leaked callback URL cannot be replayed later.
        """
        if not state:
            return False
        now = time.time()
        with self._lock:
            self._pending_states = {
                s: ts for s, ts in self._pending_states.items()
                if now - ts < STATE_TTL_SECONDS
            }
            match = next(
                (s for s in self._pending_states if hmac.compare_digest(s, state)), None
            )
            if match is None:
                logger.warning("OAuth callback rejected: unknown or expired state")
                return False
            del self._pending_states[match]
            return True

    def exchange_code(self, code: str) -> GoogleTokens:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        req = urllib.request.Request(
            GOOGLE_TOKEN_ENDPOINT,
            data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            tok = json.loads(r.read())
        self.tokens = GoogleTokens(
            access_token=tok.get("access_token", ""),
            refresh_token=tok.get("refresh_token", "") or self.tokens.refresh_token,
            expires_at=time.time() + tok.get("expires_in", 3600),
            scopes=self.scopes,
        )
        self._save()
        return self.tokens

    # ---- authenticated API calls ----
    def _ensure_access_token(self) -> str:
        if self.tokens.access_token and self.tokens.expires_at > time.time() + 60:
            return self.tokens.access_token
        if self.tokens.refresh_token:
            self._refresh()
            return self.tokens.access_token
        raise RuntimeError("No valid Google access token; complete the OAuth flow first.")

    def _refresh(self) -> None:
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.tokens.refresh_token,
            "grant_type": "refresh_token",
        }
        req = urllib.request.Request(
            GOOGLE_TOKEN_ENDPOINT,
            data=urllib.parse.urlencode(data).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            tok = json.loads(r.read())
        self.tokens.access_token = tok.get("access_token", self.tokens.access_token)
        self.tokens.expires_at = time.time() + tok.get("expires_in", 3600)
        self._save()

    def api_call(
        self,
        method: str,
        url: str,
        body: Optional[Any] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Any:
        token = self._ensure_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        if extra_headers:
            headers.update(extra_headers)
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read() or b"{}")

    # ---- token persistence (local file) ----
    def _load(self) -> GoogleTokens:
        try:
            with open(self.token_path, "r", encoding="utf-8") as f:
                return GoogleTokens(**json.load(f))
        except FileNotFoundError:
            return GoogleTokens()
        except Exception as exc:
            logger.warning("Could not read %s: %s", self.token_path, exc)
            return GoogleTokens()

    def _save(self) -> None:
        """Persist tokens, restricting access to the current user where possible."""
        try:
            fd = os.open(self.token_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.tokens.__dict__, f)
        except Exception as exc:
            logger.warning("Could not write %s: %s", self.token_path, exc)
