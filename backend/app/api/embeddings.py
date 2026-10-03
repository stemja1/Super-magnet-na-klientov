"""Embeddings API: upsert documents, semantic search. Auth required."""
from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.auth import get_current_user
from app.services.embeddings import embedder, store

router = APIRouter(
    prefix="/api/embeddings",
    tags=["embeddings"],
    dependencies=[Depends(get_current_user)],
)


class EmbedUpsert(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    doc_id: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


@router.get("/info")
def info():
    """Report which embedding backend is active and whether search is semantic."""
    semantic = embedder.is_semantic
    return {
        "backend": "sentence-transformers" if semantic else "hashing",
        "semantic": semantic,
        "dim": embedder.dim,
        "documents": len(store),
        "warning": (
            None
            if semantic
            else "sentence-transformers nie je nainštalované; vektory sú hashované, nie sémantické"
        ),
    }


@router.post("/upsert")
def upsert(req: EmbedUpsert):
    vec = embedder.embed([req.text])[0]
    counts = store.add(vec.reshape(1, -1), [req.doc_id], [req.metadata])
    return {"status": "ok", "doc_id": req.doc_id, **counts, "total": len(store)}


@router.delete("/{doc_id}")
def delete(doc_id: str):
    if not store.delete(doc_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dokument nenájdený")
    return {"status": "deleted", "doc_id": doc_id, "total": len(store)}


@router.get("/search")
def search(q: str = Query(..., min_length=1), top_k: int = Query(5, ge=1, le=50)):
    if not q.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Chýba parameter q")
    vec = embedder.embed([q])[0]
    results: List[Dict[str, Any]] = store.search(vec, top_k)
    return {"query": q, "results": results, "total_documents": len(store)}
