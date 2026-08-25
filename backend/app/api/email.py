"""Email API: Gmail OAuth + send (auth required for send)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.email.gmail import GmailConnector, get_client

router = APIRouter(prefix="/api/email", tags=["email"])


class SendEmailRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    to: str
    subject: str
    body: str
    lead_id: Optional[int] = None


@router.get("/status")
def status():
    client = get_client()
    return {"configured": client.is_configured(), "mode": client.mode()}


@router.get("/auth-url")
def auth_url():
    client = get_client()
    if not client.is_configured():
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            "Gmail OAuth nie je nakonfigurované (nastav GMAIL_CLIENT_ID/SECRET)",
        )
    url, _ = client.get_auth_url()
    return {"url": url}


@router.get("/callback")
def callback(code: str = Query(...), state: str = Query(...)):
    client = get_client()
    if not client.is_configured():
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "Gmail OAuth nie je nakonfigurované")
    client.exchange_code(code)
    return {"ok": True, "state": state}


@router.post("/send")
def send_email(
    req: SendEmailRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = GmailConnector().send_email(to=req.to, subject=req.subject, body=req.body)
    return result
