"""Sequence ORM models (email cadences)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Sequence(Base):
    __tablename__ = "sequences"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    # steps: [{"delay_hours": 24, "subject": "...", "body": "..."}]
    steps = Column(JSON, default=list)
    created_at = Column(DateTime, default=_now)

    enrollments: List["SequenceEnrollment"] = relationship(
        "SequenceEnrollment", backref="sequence", cascade="all, delete-orphan"
    )


class SequenceEnrollment(Base):
    __tablename__ = "sequence_enrollments"

    id = Column(Integer, primary_key=True, index=True)
    sequence_id = Column(Integer, ForeignKey("sequences.id"), index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), index=True)
    step_index = Column(Integer, default=0)
    status = Column(String(20), default="active")  # active | done | paused
    next_run_at = Column(DateTime, default=_now)
