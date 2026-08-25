"""Embeddings API: upsert documents, semantic search. Auth required."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.api.auth import get_current_user
from app.services.embeddings import embedder, store

router = APIRouter(
    prefix="/api/embeddings",
    tags=["embeddings"],
    dependencies=[Depends(get_current_user)],
)


class EmbedUpsert(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    doc_id: str
    text: str
    metadata: Dict[str, Any] = {}


@router.post("/upsert")
def upsert(req: EmbedUpsert):
    vec = embedder.embed([req.text])[0]
    store.add(vec.reshape(1, -1), [req.doc_id], [req.metadata])
    return {"status": "ok", "doc_id": req.doc_id}


@router.get("/search")
def search(q: str = Query(..., min_length=1), top_k: int = Query(5, ge=1, le=50)):
    if not q.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Chýba parameter q")
    vec = embedder.embed([q])[0]
    results: List[Dict[str, Any]] = store.search(vec, top_k)
    return {"query": q, "results": results}
