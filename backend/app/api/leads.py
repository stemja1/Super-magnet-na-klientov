"""Leads API: CRUD, CSV import, LLM scoring. Auth required."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.lead import Lead
from app.models.user import User
from app.schemas_lead import LeadCreate, LeadOut, LeadUpdate
from app.services import leads as leads_svc

router = APIRouter(
    prefix="/api/leads",
    tags=["leads"],
    dependencies=[Depends(get_current_user)],
)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=LeadOut)
def create_lead(data: LeadCreate, db: Session = Depends(get_db)):
    return leads_svc.create_lead(db, data)


@router.get("", response_model=list[LeadOut])
def list_leads(
    db: Session = Depends(get_db),
    company_name: Optional[str] = None,
    sector: Optional[str] = None,
    min_score: Optional[float] = None,
    enriched: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
):
    return leads_svc.list_leads(
        db,
        company_name=company_name,
        sector=sector,
        min_score=min_score,
        enriched=enriched,
        skip=skip,
        limit=limit,
    )


@router.get("/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    lead = leads_svc.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead nenájdený")
    return lead


@router.put("/{lead_id}", response_model=LeadOut)
def update_lead(lead_id: int, data: LeadUpdate, db: Session = Depends(get_db)):
    lead = leads_svc.update_lead(db, lead_id, data)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead nenájdený")
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_200_OK)
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    if not leads_svc.delete_lead(db, lead_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead nenájdený")
    return {"deleted": lead_id}


MAX_IMPORT_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_leads(
    file: UploadFile = File(...),
    enrich: bool = True,
    db: Session = Depends(get_db),
):
    """Import leads from CSV.

    Enrichment performs one ORSR HTTP request per row, so it runs in a worker
    thread to keep the event loop responsive; pass ``enrich=false`` for large
    files.
    """
    content = await file.read()
    if len(content) > MAX_IMPORT_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"CSV je príliš veľký (max {MAX_IMPORT_BYTES // (1024 * 1024)} MB)",
        )
    return await run_in_threadpool(leads_svc.import_csv, db, content, enrich)


@router.post("/{lead_id}/score")
def score_lead(lead_id: int, db: Session = Depends(get_db)):
    lead: Lead | None = leads_svc.get_lead(db, lead_id)
    if not lead:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Lead nenájdený")
    s = leads_svc.score_lead(lead)
    lead.score = s
    db.commit()
    return {"lead_id": lead_id, "score": s}
