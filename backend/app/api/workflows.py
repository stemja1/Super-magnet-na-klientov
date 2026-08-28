"""Workflows API: build and execute JSON-defined workflows for a lead."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.lead import Lead
from app.models.sequence import Workflow, WorkflowRun
from app.models.user import User
from app.services import workflows as wf_svc
from app.services.workflows.engine import execute_workflow

router = APIRouter(
    prefix="/api/workflows",
    tags=["workflows"],
    dependencies=[Depends(get_current_user)],
)


class WorkflowCreate(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    name: str
    definition: dict = {"steps": []}


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    workflow_id: int
    lead_id: int


def _run(db: Session, workflow_id: int, lead_id: int, connector=None) -> dict:
    wf = db.get(Workflow, workflow_id)
    lead = db.get(Lead, lead_id)
    if not wf or not lead:
        raise HTTPException(404, "Workflow alebo lead nenájdený")
    steps = execute_workflow(wf.definition, lead, db, connector)
    run = WorkflowRun(workflow_id=workflow_id, lead_id=lead_id, result={"steps": steps})
    db.add(run)
    db.commit()
    db.refresh(run)
    return {"workflow_id": workflow_id, "lead_id": lead_id, "steps": steps, "run_id": run.id}


@router.post("", status_code=201)
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
        raise HTTPException(404, "Workflow nenájdený")
    return wf


@router.post("/execute", status_code=200)
def execute(req: ExecuteRequest, db: Session = Depends(get_db)):
    return _run(db, req.workflow_id, req.lead_id)


@router.post("/{wid}/execute")
def execute_id(wid: int, body: dict, db: Session = Depends(get_db)):
    lead_id = body.get("lead_id")
    if not lead_id:
        raise HTTPException(400, "lead_id is required")
    return _run(db, wid, lead_id)
