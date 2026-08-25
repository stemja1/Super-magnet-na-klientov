"""Google Sheets / Docs connector with sandbox fallback (spec §4)."""
from __future__ import annotations

import os
import uuid
from typing import List, Optional

from app.services.integrations.google_oauth import GoogleOAuthClient

SCOPES = (
    "https://www.googleapis.com/auth/spreadsheets "
    "https://www.googleapis.com/auth/documents"
)


def _make_client() -> GoogleOAuthClient:
    return GoogleOAuthClient(
        client_id=os.getenv("GOOGLE_CLIENT_ID", os.getenv("GMAIL_CLIENT_ID", "")),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", os.getenv("GMAIL_CLIENT_SECRET", "")),
        redirect_uri=os.getenv(
            "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/export/callback"
        ),
        scopes=SCOPES,
        token_path=os.getenv("GOOGLE_TOKEN_PATH", ".google_tokens.json"),
    )


_client: Optional[GoogleOAuthClient] = None


def get_client() -> GoogleOAuthClient:
    global _client
    if _client is None:
        _client = _make_client()
    return _client


class SheetsDocsConnector:
    def __init__(self, client: Optional[GoogleOAuthClient] = None) -> None:
        self.client = client or get_client()

    def append_rows(self, spreadsheet_id: str, rows: List[List[str]], range: str = "Sheet1") -> dict:
        if self.client.mode() == "sandbox":
            return {"status": "simulated", "appended": len(rows), "mode": "sandbox"}
        url = (
            f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}"
            f"/values/{range}:append?valueInputOption=USER_ENTERED"
        )
        self.client.api_call("POST", url, {"values": rows})
        return {"status": "ok", "appended": len(rows), "mode": "live"}

    def create_doc(self, title: str, text: str = "") -> dict:
        if self.client.mode() == "sandbox":
            return {
                "status": "simulated",
                "documentId": f"sandbox-{uuid.uuid4().hex[:12]}",
                "mode": "sandbox",
            }
        doc = self.client.api_call(
            "POST", "https://docs.googleapis.com/v1/documents", {"title": title}
        )
        doc_id = doc.get("documentId")
        if text:
            self.client.api_call(
                "POST",
                f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
                {"requests": [{"insertText": {"location": {"index": 1}, "text": text}}]},
            )
        return {"status": "ok", "documentId": doc_id, "mode": "live"}
