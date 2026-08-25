"""LLM API router — local prompt execution with mock fallback."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.schemas import LLMPromptRequest, LLMPromptResponse
from app.services.llm_orchestrator import orchestrator

router = APIRouter(tags=["llm"])


@router.post(
    "/llm/prompt",
    response_model=LLMPromptResponse,
    summary="Spusti lokálny LLM prompt",
)
def prompt(req: LLMPromptRequest):
    """Odošle prompt do LLM Orchestratora.

    Použije reálny llama.cpp model, ak je dostupný; inak deterministický
    mock režim, takže API je vždy volateľné (CI, vývoj).
    """
    try:
        result = orchestrator.generate(
            req.prompt,
            model_hint=req.model_hint,
            top_k=req.top_k,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
            use_rag=req.use_rag,
        )
        return LLMPromptResponse(**result)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {exc}")


@router.get("/llm/status", summary="Stav LLM Orchestratora")
def status():
    return {
        "backend": orchestrator.backend,
        "model": getattr(orchestrator, "model_path", "") or "mock",
        "model_loaded": orchestrator.backend != "mock",
    }
