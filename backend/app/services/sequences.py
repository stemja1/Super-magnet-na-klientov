"""Sequence business logic: create, enroll, A/B variants, run due steps."""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.sequence import Sequence, SequenceEnrollment
from app.services.email.gmail import GmailConnector


def create_sequence(
    db: Session,
    name: str,
    steps: Optional[List[dict]] = None,
    ab_enabled: bool = False,
    variants: Optional[Dict[str, List[dict]]] = None,
) -> Sequence:
    seq = Sequence(
        name=name,
        steps=steps or [],
        ab_enabled=ab_enabled,
        variants=variants,
    )
    db.add(seq)
    db.commit()
    db.refresh(seq)
    return seq


def list_sequences(db: Session) -> List[Sequence]:
    return db.query(Sequence).order_by(Sequence.id.desc()).all()


def get_sequence(db: Session, sid: int) -> Optional[Sequence]:
    return db.get(Sequence, sid)


def enroll(db: Session, sid: int, lead_ids: List[int]) -> dict:
    seq = db.get(Sequence, sid)
    if not seq:
        return {"enrolled": 0}
    count = 0
    for lid in lead_ids:
        if db.get(Lead, lid) is None:
            continue
        variant = (
            random.choice(["A", "B"]) if seq.ab_enabled else "A"
        )
        db.add(
            SequenceEnrollment(
                sequence_id=sid,
                lead_id=lid,
                step_index=0,
                status="active",
                variant=variant,
                next_run_at=datetime.now(timezone.utc),
            )
        )
        count += 1
    db.commit()
    return {"enrolled": count, "ab_enabled": seq.ab_enabled}


def _variant_steps(seq: Sequence, variant: str) -> List[dict]:
    if seq.ab_enabled and seq.variants:
        return seq.variants.get(variant, seq.steps) or []
    return seq.steps or []


def _render(template: str, lead: Lead) -> str:
    try:
        return template.format(
            company_name=lead.company_name or "",
            contact_name=lead.contact_name or "",
            email=lead.email or "",
        )
    except Exception:
        return template


def run_due(
    db: Session,
    now: Optional[datetime] = None,
    connector=None,
    sequence_id: Optional[int] = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    connector = connector or GmailConnector()
    q = db.query(SequenceEnrollment).filter(
        SequenceEnrollment.status == "active", SequenceEnrollment.next_run_at <= now
    )
    if sequence_id is not None:
        q = q.filter(SequenceEnrollment.sequence_id == sequence_id)
    due = q.all()
    sent = 0
    for enr in due:
        seq = db.get(Sequence, enr.sequence_id)
        lead = db.get(Lead, enr.lead_id)
        steps = _variant_steps(seq, enr.variant) if seq else []
        if not lead or enr.step_index >= len(steps):
            enr.status = "done"
            continue
        step = steps[enr.step_index]
        subject = _render(step.get("subject", ""), lead)
        body = _render(step.get("body", ""), lead)
        if lead.email:
            connector.send_email(to=lead.email, subject=subject, body=body)
            sent += 1
        enr.step_index += 1
        if enr.step_index >= len(steps):
            enr.status = "done"
        else:
            delay = int(steps[enr.step_index].get("delay_hours", 24))
            enr.next_run_at = now + timedelta(hours=delay)
    db.commit()
    return {"processed": len(due), "sent": sent}


def ab_report(db: Session, sid: int) -> dict:
    enrollments = (
        db.query(SequenceEnrollment)
        .filter(SequenceEnrollment.sequence_id == sid)
        .all()
    )
    counts = {"A": 0, "B": 0, "total": len(enrollments)}
    for e in enrollments:
        if e.variant in counts:
            counts[e.variant] += 1
    return counts
