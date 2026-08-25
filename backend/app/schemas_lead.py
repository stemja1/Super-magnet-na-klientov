"""Lead request/response schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

_CFG = ConfigDict(protected_namespaces=(), from_attributes=True)


class LeadCreate(BaseModel):
    model_config = _CFG
    company_name: str = Field(min_length=1, max_length=200)
    ico: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    sector: Optional[str] = None
    company_size: Optional[str] = None
    source: str = "manual"
    notes: Optional[str] = None


class LeadUpdate(BaseModel):
    model_config = _CFG
    company_name: Optional[str] = None
    ico: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    sector: Optional[str] = None
    company_size: Optional[str] = None
    notes: Optional[str] = None


class LeadOut(BaseModel):
    model_config = _CFG
    id: int
    company_name: str
    ico: Optional[str] = None
    contact_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    sector: Optional[str] = None
    company_size: Optional[str] = None
    source: str
    score: Optional[float] = None
    enriched: int
    notes: Optional[str] = None
