"""Sequences API: create cadences, enroll leads, run due steps."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.sequence import Sequence
from app.models.user import User
from app.services import sequences as seq_svc

router = APIRouter(
    prefix="/api/sequences",
    tags=["sequences"],
    dependencies=[Depends(get_current_user)],
)


class Step(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    delay_hours: int = 24
    subject: str = ""
    body: str = ""


class SequenceCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str = Field(min_length=1, max_length=200)
    steps: List[Step] = []
    ab_enabled: bool = False
    variants: Optional[Dict[str, List[Step]]] = None


class EnrollRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    lead_ids: List[int]


@router.post("", status_code=201)
def create_sequence(data: SequenceCreate, db: Session = Depends(get_db)):
    steps = [s.model_dump() for s in data.steps]
    variants = (
        {k: [s.model_dump() for s in v] for k, v in (data.variants or {}).items()}
        if data.variants
        else None
    )
    return seq_svc.create_sequence(
        db, data.name, steps, ab_enabled=data.ab_enabled, variants=variants
    )


@router.get("")
def list_sequences(db: Session = Depends(get_db)):
    return seq_svc.list_sequences(db)


@router.get("/{sid}")
def get_sequence(sid: int, db: Session = Depends(get_db)):
    seq = seq_svc.get_sequence(db, sid)
    if not seq:
        raise HTTPException(404, "Sekvencia nenájdená")
    return seq


@router.post("/{sid}/enroll")
def enroll(sid: int, data: EnrollRequest, db: Session = Depends(get_db)):
    if not seq_svc.get_sequence(db, sid):
        raise HTTPException(404, "Sekvencia nenájdená")
    return seq_svc.enroll(db, sid, data.lead_ids)


@router.get("/{sid}/ab-report")
def ab_report(sid: int, db: Session = Depends(get_db)):
    if not seq_svc.get_sequence(db, sid):
        raise HTTPException(404, "Sekvencia nenájdená")
    return seq_svc.ab_report(db, sid)


@router.post("/{sid}/run")
def run(sid: int, db: Session = Depends(get_db)):
    if not seq_svc.get_sequence(db, sid):
        raise HTTPException(404, "Sekvencia nenájdená")
    return seq_svc.run_due(db, now=datetime.now(timezone.utc), sequence_id=sid)
