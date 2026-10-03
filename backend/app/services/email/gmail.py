"""Gmail connector — send email via Gmail API (OAuth) with sandbox fallback.

Live mode builds an RFC822 message and POSTs it to the Gmail API. When no
OAuth credentials are configured it runs in **sandbox** mode and returns a
simulated message id, so the endpoint is fully testable offline.
"""
from __future__ import annotations

import base64
import email
import os
import uuid
from typing import Optional

from app.services.integrations.google_oauth import GoogleOAuthClient

SCOPES = (
    "https://www.googleapis.com/auth/gmail.send "
    "https://www.googleapis.com/auth/gmail.compose"
)


def _make_client() -> GoogleOAuthClient:
    return GoogleOAuthClient(
        client_id=os.getenv("GMAIL_CLIENT_ID", ""),
        client_secret=os.getenv("GMAIL_CLIENT_SECRET", ""),
        redirect_uri=os.getenv(
            "GMAIL_REDIRECT_URI", "http://localhost:8000/api/email/callback"
        ),
        scopes=SCOPES,
        token_path=os.getenv("GMAIL_TOKEN_PATH", ".gmail_tokens.json"),
    )


_client: Optional[GoogleOAuthClient] = None


def get_client() -> GoogleOAuthClient:
    global _client
    if _client is None:
        _client = _make_client()
    return _client


class GmailConnector:
    def __init__(self, client: Optional[GoogleOAuthClient] = None) -> None:
        self.client = client or get_client()

    def send_email(self, to: str, subject: str, body: str) -> dict:
        if self.client.mode() == "sandbox":
            return {"message_id": f"sandbox-{uuid.uuid4().hex[:12]}", "mode": "sandbox"}

        msg = email.message.EmailMessage()
        msg["To"] = to
        # No From header: Gmail fills in the authenticated mailbox. Writing
        # "From: me" produces a malformed RFC822 message that the API rejects.
        msg["Subject"] = subject
        msg.set_content(body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        resp = self.client.api_call(
            "POST",
            "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            {"raw": raw},
        )
        return {"message_id": resp.get("id"), "mode": "live"}
