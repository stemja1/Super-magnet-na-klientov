"""Lead business logic: CRUD, CSV import, ORSR enrichment, LLM scoring."""
from __future__ import annotations

import csv
import io
import logging
import re
from typing import Optional

from sqlalchemy.orm import Session

from app.llm_orchestrator.prompts import LEAD_SCORING_TEMPLATE
from app.models.lead import Lead
from app.schemas_lead import LeadCreate, LeadUpdate
from app.services.enrichment.orsr import orsr
from app.services.llm_orchestrator import orchestrator

logger = logging.getLogger("leads")


# ---- enrichment -----------------------------------------------------------
def _enrich(lead: Lead) -> None:
    if not lead.ico:
        return
    try:
        prof = orsr.get_by_ico(lead.ico)
        if not lead.company_name:
            lead.company_name = prof.name
        if not lead.sector and prof.legal_form:
            lead.sector = prof.legal_form
        lead.enriched = 1
    except Exception as exc:  # pragma: no cover - connector is graceful
        logger.warning("Enrichment failed for %s: %s", lead.ico, exc)


# ---- CRUD -----------------------------------------------------------------
def create_lead(db: Session, data: LeadCreate, enrich: bool = True) -> Lead:
    lead = Lead(**data.model_dump(exclude_none=True))
    if enrich:
        _enrich(lead)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    return lead


def list_leads(
    db: Session,
    *,
    company_name: Optional[str] = None,
    sector: Optional[str] = None,
    min_score: Optional[float] = None,
    enriched: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> list[Lead]:
    q = db.query(Lead)
    if company_name:
        q = q.filter(Lead.company_name.ilike(f"%{company_name}%"))
    if sector:
        q = q.filter(Lead.sector == sector)
    if min_score is not None:
        q = q.filter(Lead.score >= min_score)
    if enriched is not None:
        q = q.filter(Lead.enriched == (1 if enriched else 0))
    return q.order_by(Lead.id.desc()).offset(skip).limit(limit).all()


def get_lead(db: Session, lead_id: int) -> Optional[Lead]:
    return db.get(Lead, lead_id)


def update_lead(db: Session, lead_id: int, data: LeadUpdate) -> Optional[Lead]:
    lead = db.get(Lead, lead_id)
    if not lead:
        return None
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    db.commit()
    db.refresh(lead)
    return lead


def delete_lead(db: Session, lead_id: int) -> bool:
    lead = db.get(Lead, lead_id)
    if not lead:
        return False
    db.delete(lead)
    db.commit()
    return True


# ---- CSV import -----------------------------------------------------------
def import_csv(db: Session, content: bytes, enrich: bool = True) -> dict:
    """Import leads from CSV bytes.

    ``enrich`` triggers a synchronous ORSR lookup per row, which is one HTTP
    request each — pass ``enrich=False`` for large files and enrich later
    (or via the background worker planned for the next phase).
    """
    text = content.decode("utf-8-sig", "ignore")
    reader = csv.DictReader(io.StringIO(text))
    created = 0
    errors: list[dict] = []
    for i, row in enumerate(reader, start=1):
        try:
            data = LeadCreate(
                company_name=row.get("company_name") or row.get("nazov") or row.get("name"),
                ico=row.get("ico") or row.get("ICO"),
                contact_name=row.get("contact_name") or row.get("kontakt"),
                email=row.get("email"),
                phone=row.get("phone") or row.get("telefon"),
                sector=row.get("sector") or row.get("odvetvie"),
                company_size=row.get("company_size") or row.get("velkost"),
                source="csv_import",
                notes=row.get("notes") or row.get("poznamka"),
            )
            create_lead(db, data, enrich=enrich)
            created += 1
        except Exception as exc:
            errors.append({"row": i, "error": str(exc)})
    return {"created": created, "errors": errors, "enriched": bool(enrich)}


# ---- LLM lead scoring (spec §8) ------------------------------------------
def _company_profile(lead: Lead) -> str:
    return (
        f"Názov: {lead.company_name}; IČO: {lead.ico or '?'}; "
        f"Odvetvie: {lead.sector or '?'}; Veľkosť: {lead.company_size or '?'}"
    )


def _contact_profile(lead: Lead) -> str:
    return f"Meno: {lead.contact_name or '?'}; Email: {lead.email or '?'}"


def _heuristic_score(lead: Lead) -> float:
    """Deterministic fallback used when no local model is loaded."""
    base = 50.0
    if lead.ico:
        base += 10
    if lead.email:
        base += 10
    if lead.sector:
        base += 5
    if lead.company_size and any(c.isdigit() for c in str(lead.company_size)):
        base += 5
    return float(min(100, base))


# Score extraction, most explicit form first. A bare "\b\d{1,3}\b" fallback would
# happily return the first unrelated number in a prose answer ("3 dôvody..." -> 3).
_SCORE_PATTERNS = (
    re.compile(r"sk[óo]re\s*[:=]\s*(\d{1,3})", re.IGNORECASE),
    re.compile(r"(\d{1,3})\s*/\s*100"),
    re.compile(r"(\d{1,3})\s*%", re.IGNORECASE),
    re.compile(r"^\s*(\d{1,3})\s*$", re.MULTILINE),
)


def parse_score(text: str) -> Optional[float]:
    """Extract a 0-100 lead score from free-form model output.

    Returns ``None`` when no score is present, so callers can fall back instead of
    silently scoring a lead 0.
    """
    if not text:
        return None
    for pattern in _SCORE_PATTERNS:
        m = pattern.search(text)
        if m:
            return float(min(100, max(0, int(m.group(1)))))
    return None


def score_lead(lead: Lead) -> float:
    """Score a lead 0-100 via the local LLM; deterministic heuristic in mock mode."""
    if orchestrator.backend == "mock":
        return _heuristic_score(lead)

    prompt = LEAD_SCORING_TEMPLATE.format(
        company_profile=_company_profile(lead),
        contact_profile=_contact_profile(lead),
        recent_activity=lead.notes or "žiadna",
    )
    res = orchestrator.generate(prompt, model_hint="7b", max_tokens=200, temperature=0.3)
    parsed = parse_score(res.get("text", ""))
    if parsed is None:
        logger.warning(
            "LLM score for lead %s unparseable; using heuristic", lead.id
        )
        return _heuristic_score(lead)
    return parsed
