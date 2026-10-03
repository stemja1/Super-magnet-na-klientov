"""Email API: Gmail OAuth + send (auth required for send).

``/status`` and ``/auth-url`` stay public because the desktop UI needs to decide
whether to show the connect button before the user has a token; ``/callback`` is
reachable by the browser during the redirect and validates the OAuth ``state``.
Everything that sends mail requires a valid JWT.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.email.deliverability import DeliverabilityChecker
from app.services.email.gmail import GmailConnector, get_client

router = APIRouter(prefix="/api/email", tags=["email"])


class DeliverabilityRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    domain: str


@router.post("/deliverability")
def deliverability(req: DeliverabilityRequest, _: User = Depends(get_current_user)):
    return DeliverabilityChecker().check(req.domain)


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
            "Gmail OAuth nie je nakonfigurovaný (nastav GMAIL_CLIENT_ID/SECRET)",
        )
    url, state = client.get_auth_url()
    return {"url": url, "state": state}


@router.get("/callback")
def callback(code: str = Query(...), state: str = Query(...)):
    client = get_client()
    if not client.is_configured():
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST, "Gmail OAuth nie je nakonfigurovaný"
        )
    # The state was issued by /auth-url; without this check an attacker could feed
    # a victim their own authorization code (CSRF on the OAuth flow).
    if not client.consume_state(state):
        raise HTTPException(
            http_status.HTTP_400_BAD_REQUEST,
            "Neplatný alebo expirovaný OAuth state — začni prihlasenie znova",
        )
    client.exchange_code(code)
    return {"ok": True}


class SendEmailRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    to: str
    subject: str
    body: str
    lead_id: Optional[int] = None


@router.post("/send")
def send_email(
    req: SendEmailRequest,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return GmailConnector().send_email(to=req.to, subject=req.subject, body=req.body)
