"""Lead ORM model (B2B prospects for the Slovak market)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db.session import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Lead(Base):
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String(200), index=True, nullable=False)
    ico = Column(String(20), index=True, nullable=True)  # IČO (Slovak reg. no.)
    contact_name = Column(String(200), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(50), nullable=True)
    sector = Column(String(100), nullable=True)
    company_size = Column(String(50), nullable=True)
    source = Column(String(50), default="manual")
    score = Column(Float, nullable=True)  # 0-100 lead score
    notes = Column(Text, nullable=True)
    enriched = Column(Integer, default=0)  # 0 = no, 1 = ORSR enriched
    created_at = Column(DateTime, default=_now)
    updated_at = Column(DateTime, default=_now, onupdate=_now)
