"""Sequence business logic: create, enroll, A/B variants, run due steps."""
from __future__ import annotations

import logging
import random
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.lead import Lead
from app.models.sequence import Sequence, SequenceEnrollment
from app.services.email.gmail import GmailConnector

logger = logging.getLogger("sequences")


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


def _variant_steps(seq: Sequence, variant: str) -> List[dict]:
    if seq.ab_enabled and seq.variants:
        return seq.variants.get(variant) or seq.steps or []
    return seq.steps or []


# Slots available in subject/body templates.
_TEMPLATE_SLOTS = {
    "company_name": lambda lead: lead.company_name or "",
    "contact_name": lambda lead: lead.contact_name or "",
    "email": lambda lead: lead.email or "",
    "ico": lambda lead: lead.ico or "",
    "sector": lambda lead: lead.sector or "",
}

_PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


def _render(template: str, lead: Lead) -> str:
    """Fill ``{slot}`` placeholders without executing arbitrary format specs.

    ``str.format`` on user-authored templates raises on unknown keys and would
    evaluate format specs. Substituting literally keeps a template containing
    ``{0}`` or ``{company_name!r}`` from breaking the run or leaking internals.
    Unknown slots are left untouched so typos stay visible.
    """
    if not template:
        return ""

    def repl(match: "re.Match[str]") -> str:
        getter = _TEMPLATE_SLOTS.get(match.group(1))
        return getter(lead) if getter else match.group(0)

    return _PLACEHOLDER.sub(repl, template)


def enroll(db: Session, sid: int, lead_ids: List[int]) -> dict:
    seq = db.get(Sequence, sid)
    if not seq:
        return {"enrolled": 0, "skipped_duplicates": 0, "ab_enabled": False}

    # Idempotency: never enroll the same lead twice into one sequence, otherwise a
    # retried request delivers duplicate emails.
    existing = {
        row[0]
        for row in db.query(SequenceEnrollment.lead_id)
        .filter(
            SequenceEnrollment.sequence_id == sid,
            SequenceEnrollment.lead_id.in_(lead_ids),
        )
        .all()
    }

    count = 0
    skipped = 0
    for lid in lead_ids:
        if db.get(Lead, lid) is None:
            continue
        if lid in existing:
            skipped += 1
            continue
        existing.add(lid)
        db.add(
            SequenceEnrollment(
                sequence_id=sid,
                lead_id=lid,
                step_index=0,
                status="active",
                variant=random.choice(["A", "B"]) if seq.ab_enabled else "A",
                next_run_at=datetime.now(timezone.utc),
            )
        )
        count += 1
    db.commit()
    return {"enrolled": count, "skipped_duplicates": skipped, "ab_enabled": seq.ab_enabled}


def run_due(
    db: Session,
    now: Optional[datetime] = None,
    connector=None,
    sequence_id: Optional[int] = None,
) -> dict:
    """Send every enrollment step whose scheduled time has arrived.

    Each enrollment is isolated: one failing send is recorded and the batch
    continues, instead of aborting the whole run and leaving the rest in an
    undefined state.
    """
    now = now or datetime.now(timezone.utc)
    connector = connector or GmailConnector()
    q = db.query(SequenceEnrollment).filter(
        SequenceEnrollment.status == "active", SequenceEnrollment.next_run_at <= now
    )
    if sequence_id is not None:
        q = q.filter(SequenceEnrollment.sequence_id == sequence_id)
    due = q.all()

    sent = 0
    failed = 0
    skipped = 0
    for enr in due:
        seq = db.get(Sequence, enr.sequence_id)
        lead = db.get(Lead, enr.lead_id)
        steps = _variant_steps(seq, enr.variant) if seq else []
        if not lead or not steps or enr.step_index >= len(steps):
            enr.status = "done"
            continue

        step = steps[enr.step_index]
        if not lead.email:
            skipped += 1
            enr.step_index += 1
            enr.status = (
                "done" if enr.step_index >= len(steps) else enr.status
            )
            if enr.status != "done":
                delay = int(steps[enr.step_index].get("delay_hours", 24))
                enr.next_run_at = now + timedelta(hours=delay)
            continue

        try:
            connector.send_email(
                to=lead.email,
                subject=_render(step.get("subject", ""), lead),
                body=_render(step.get("body", ""), lead),
            )
        except Exception as exc:
            # Park the enrollment instead of retrying forever on the same tick.
            failed += 1
            enr.status = "failed"
            logger.warning(
                "Sequence %s step %s for lead %s failed: %s",
                enr.sequence_id, enr.step_index, enr.lead_id, exc,
            )
            continue

        sent += 1
        enr.step_index += 1
        if enr.step_index >= len(steps):
            enr.status = "done"
        else:
            delay = int(steps[enr.step_index].get("delay_hours", 24))
            enr.next_run_at = now + timedelta(hours=delay)

    db.commit()
    return {
        "processed": len(due),
        "sent": sent,
        "failed": failed,
        "skipped_no_email": skipped,
    }


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
