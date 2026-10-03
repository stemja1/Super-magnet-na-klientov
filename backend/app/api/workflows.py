"""Workflows API: build and execute JSON-defined workflows for a lead."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.lead import Lead
from app.models.sequence import Workflow, WorkflowRun
from app.services.workflows.engine import execute_workflow

router = APIRouter(
    prefix="/api/workflows",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)],
)

MAX_DEFINITION_STEPS = 100


def _count_steps(definition: dict) -> int:
    total = 0
    for step in definition.get("steps", []) or []:
        if not isinstance(step, dict):
            continue
        total += 1
        total += _count_steps({"steps": step.get("then", []) or []})
        total += _count_steps({"steps": step.get("else", []) or []})
    return total


class WorkflowCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str = Field(min_length=1, max_length=200)
    definition: dict = Field(default_factory=lambda: {"steps": []})

    @field_validator("definition")
    @classmethod
    def _validate_definition(cls, v: dict) -> dict:
        if not isinstance(v, dict):
            raise ValueError("definition must be an object")
        steps = v.get("steps")
        if steps is not None and not isinstance(steps, list):
            raise ValueError("definition.steps must be a list")
        if _count_steps(v) > MAX_DEFINITION_STEPS:
            raise ValueError(
                f"definition exceeds {MAX_DEFINITION_STEPS} steps (nested included)"
            )
        return v


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    workflow_id: int
    lead_id: int


def _pending_run(db: Session, workflow_id: int, lead_id: int) -> Optional[WorkflowRun]:
    """Most recent run for this pair, if it is still waiting on a ``wait`` step."""
    return (
        db.query(WorkflowRun)
        .filter(
            WorkflowRun.workflow_id == workflow_id,
            WorkflowRun.lead_id == lead_id,
            WorkflowRun.status == "waiting",
        )
        .order_by(WorkflowRun.id.desc())
        .first()
    )


def _run(db: Session, workflow_id: int, lead_id: int, connector=None) -> dict:
    wf = db.get(Workflow, workflow_id)
    lead = db.get(Lead, lead_id)
    if not wf or not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow alebo lead nenájdený")

    # Resume automatically when a previous run suspended on a wait step.
    pending = _pending_run(db, workflow_id, lead_id)
    resume_after = None
    if pending is not None and isinstance(pending.result, dict):
        cursor = pending.result.get("resume_after")
        if cursor and pending.result.get("resume_at"):
            resume_at = pending.result["resume_at"]
            try:
                due = datetime.fromisoformat(resume_at) <= datetime.now(timezone.utc)
            except ValueError:
                due = True
            if due:
                resume_after = cursor

    outcome = execute_workflow(
        wf.definition, lead, db, connector, resume_after=resume_after
    )

    run = WorkflowRun(
        workflow_id=workflow_id,
        lead_id=lead_id,
        status=outcome["status"],
        result={"steps": outcome["steps"], "resume_after": outcome["resume_after"],
                "resume_at": outcome["resume_at"]},
    )
    db.add(run)
    if pending is not None and resume_after is not None:
        pending.status = "resumed"
    db.commit()
    db.refresh(run)

    return {
        "workflow_id": workflow_id,
        "lead_id": lead_id,
        "run_id": run.id,
        "status": outcome["status"],
        "steps": outcome["steps"],
        "resume_at": outcome["resume_at"],
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_workflow(data: WorkflowCreate, db: Session = Depends(get_db)):
    wf = Workflow(name=data.name, definition=data.definition)
    db.add(wf)
    db.commit()
    db.refresh(wf)
    return wf


@router.get("")
def list_workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).order_by(Workflow.id.desc()).all()


@router.get("/{wid}")
def get_workflow(wid: int, db: Session = Depends(get_db)):
    wf = db.get(Workflow, wid)
    if not wf:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workflow nenájdený")
    return wf


@router.post("/execute")
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
    return _run(db, req.workflow_id, req.lead_id)


@router.post("/{wid}/execute")
def execute_id(wid: int, body: dict, db: Session = Depends(get_db)):
    lead_id = body.get("lead_id")
    if not lead_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "lead_id is required")
    return _run(db, wid, lead_id)
