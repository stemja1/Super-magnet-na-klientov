"""Transcription API: whisper.cpp transcribe + LLM call insights."""
from __future__ import annotations

import os
import tempfile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.transcription import TranscriptionService

router = APIRouter(
    prefix="/api/transcription",
    tags=["transcription"],
    dependencies=[Depends(get_current_user)],
)

_service = TranscriptionService()


class InsightsRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    transcript: str


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...), _: User = Depends(get_current_user)):
    suffix = os.path.splitext(file.filename or ".wav")[1] or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(await file.read())
        path = tmp.name
    try:
        return _service.transcribe(path)
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


@router.post("/insights")
def insights(req: InsightsRequest, _: User = Depends(get_current_user)):
    if not req.transcript.strip():
        raise HTTPException(400, "Prázdny prepis")
    return _service.insights(req.transcript)
