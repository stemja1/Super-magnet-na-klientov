"""Export API: CSV (backend), Google Sheets / Docs (OAuth, sandbox fallback)."""
from __future__ import annotations

import csv
import io
from typing import List, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.lead import Lead
from app.models.user import User
from app.services.integrations.sheets_docs import SheetsDocsConnector

router = APIRouter(
    prefix="/api/export",
    tags=["export"],
    dependencies=[Depends(get_current_user)],
)

_FIELDS = [
    "id", "company_name", "ico", "contact_name", "email", "phone",
    "sector", "company_size", "score", "enriched", "source",
]

# Leading characters Excel/LibreOffice interpret as a formula. A company called
# "=cmd|'/c calc'!A1" would otherwise execute on open (CSV injection).
_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def sanitize_csv_cell(value) -> str:
    """Neutralise spreadsheet formula injection in exported cells."""
    if value is None:
        return ""
    text = str(value)
    if text.startswith(_FORMULA_PREFIXES):
        return "'" + text
    return text


@router.get("/leads.csv")
def export_leads_csv(db: Session = Depends(get_db)):
    leads = db.query(Lead).order_by(Lead.id).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(_FIELDS)
    for lead in leads:
        w.writerow([sanitize_csv_cell(getattr(lead, f)) for f in _FIELDS])
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="leads.csv"'},
    )


class SheetsExportRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    spreadsheet_id: str
    rows: Optional[List[List[str]]] = None
    range: str = "Sheet1"


class DocsExportRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    title: str
    content: Optional[str] = None


def _lead_rows(db: Session) -> List[List[str]]:
    leads = db.query(Lead).order_by(Lead.id).all()
    rows = [["id", "company_name", "ico", "email", "sector", "score"]]
    for lead in leads:
        rows.append(
            [
                str(lead.id),
                sanitize_csv_cell(lead.company_name),
                sanitize_csv_cell(lead.ico),
                sanitize_csv_cell(lead.email),
                sanitize_csv_cell(lead.sector),
                str(lead.score) if lead.score is not None else "",
            ]
        )
    return rows


@router.post("/google-sheets")
def to_sheets(req: SheetsExportRequest, db: Session = Depends(get_db)):
    rows = req.rows or _lead_rows(db)
    return SheetsDocsConnector().append_rows(req.spreadsheet_id, rows, req.range)


@router.post("/google-docs")
def to_docs(req: DocsExportRequest, db: Session = Depends(get_db)):
    text = req.content or ""
    if not text:
        leads = db.query(Lead).order_by(Lead.id).all()
        text = "\n".join(
            f"- {lead.company_name} ({lead.email or '?'})" for lead in leads
        )
    return SheetsDocsConnector().create_doc(req.title, text)
