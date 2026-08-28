"""Sequence + Workflow ORM models (email cadences, A/B variants, workflows)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Sequence(Base):
    __tablename__ = "sequences"
    __allow_unmapped__ = True

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    # Default linear steps: [{"delay_hours": 24, "subject": "...", "body": "..."}]
    steps = Column(JSON, default=list)
    # A/B testing: {"A": [...steps], "B": [...steps]} when ab_enabled.
    ab_enabled = Column(Boolean, default=False)
    variants = Column(JSON, nullable=True)
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
    variant = Column(String(10), default="A")  # A | B (for A/B tests)
    next_run_at = Column(DateTime, default=_now)


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    # JSON definition: {"steps": [{type, ...}, ...]}
    definition = Column(JSON, default=dict)
    created_at = Column(DateTime, default=_now)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id = Column(Integer, primary_key=True, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), index=True)
    lead_id = Column(Integer, nullable=True, index=True)
    status = Column(String(20), default="success")
    result = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_now)
