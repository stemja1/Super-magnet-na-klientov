"""LLM Orchestrator.

Wraps a local llama.cpp (GGUF) model with a graceful **mock fallback** so the
service is fully runnable *before* any model weights are downloaded — ideal for
CI, code review, and development on constrained hardware.

Design rules (spec §8):
  * Prefer a local 7B quantized model; fall back to 3B when RAM/VRAM is tight.
  * CPU inference (llama.cpp) when no GPU is available.
  * RAG: prepend retrieved context (max 2-3 docs) when ``use_rag`` is set.
  * Cache identical (prompt + params) generations to avoid repeat work.
"""
from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.config import BASE_DIR, settings

logger = logging.getLogger("llm_orchestrator")

VALID_HINTS = ("7b", "3b")

RAG_MAX_DOCS = 3
RAG_MAX_DOC_CHARS = 1200


def _retrieve(query: str, top_k: int = RAG_MAX_DOCS) -> List[str]:
    """Semantic retrieval over the local vector store.

    Imported lazily to keep the orchestrator importable without numpy/FAISS and
    to avoid a circular import (embeddings has no dependency on this module).
    Returns an empty list when the store is empty or unreachable.
    """
    try:
        from app.services.embeddings import embedder, store
    except Exception as exc:  # pragma: no cover - optional dependency
        logger.warning("RAG unavailable: %s", exc)
        return []

    if len(store) == 0:
        logger.debug("RAG: vector store empty, skipping retrieval")
        return []
    try:
        vec = embedder.embed([query])[0]
        hits = store.search(vec, top_k)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("RAG retrieval failed: %s", exc)
        return []
    # Only documents whose text was stored can be used as context.
    return [
        (h.get("metadata") or {}).get("text", "")[:RAG_MAX_DOC_CHARS]
        for h in hits
        if (h.get("metadata") or {}).get("text")
    ]


@dataclass
class GenerationResult:
    text: str
    backend: str
    model: str
    model_hint: Optional[str]
    tokens_used: Optional[int]
    finish_reason: Optional[str]
    cached: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "backend": self.backend,
            "model": self.model,
            "model_hint": self.model_hint,
            "tokens_used": self.tokens_used,
            "finish_reason": self.finish_reason,
            "cached": self.cached,
        }


CACHE_MAX_ENTRIES = 128


class LLMOrchestrator:
    def __init__(self) -> None:
        self.model = None
        self.backend = "mock"
        self.model_path = ""
        self._cache: "OrderedDict[str, GenerationResult]" = OrderedDict()
        self._lock = threading.Lock()  # llama.cpp context is not thread-safe
        self._load_model()

    # ---- model loading / fallback -------------------------------------
    def _resolve_model_path(self) -> str:
        path = settings.LLM_MODEL_PATH
        if path and os.path.exists(path):
            return path
        # Auto-discover a .gguf file inside the project (e.g. models/gguf).
        candidates = sorted(Path(BASE_DIR).glob("**/*.gguf"))
        if candidates:
            return str(candidates[0])
        return path or ""

    def _load_model(self) -> None:
        path = self._resolve_model_path()
        if path and os.path.exists(path):
            try:
                from llama_cpp import Llama  # optional dependency

                self.model = Llama(
                    model_path=path,
                    n_gpu_layers=settings.LLM_GPU_LAYERS,
                    n_ctx=4096,
                    verbose=False,
                )
                self.backend = "llama_cpp"
                self.model_path = path
                logger.info("LLM Orchestrator: loaded llama.cpp model from %s", path)
                return
            except Exception as exc:  # pragma: no cover - optional dependency
                logger.warning("LLM Orchestrator: llama.cpp load failed (%s); mock active", exc)
        else:
            logger.info("LLM Orchestrator: no GGUF model found -> mock backend active")

    # ---- helpers ------------------------------------------------------
    @staticmethod
    def _build_rag_prompt(query: str, contexts: List[str]) -> str:
        context_block = "\n\n".join(
            f"[Dokument {i + 1}]\n{c}" for i, c in enumerate(contexts[:RAG_MAX_DOCS])
        )
        return (
            "Nasledujúce dokumenty sú kontextom úlohy.\n\n"
            f"{context_block}\n\n"
            f"Otázka: {query}\n\n"
            "Odpovedaj na základe poskytnutého kontextu."
        )

    def _cache_key(self, prompt: str, **params: Any) -> str:
        payload = prompt + "|" + "|".join(f"{k}={v}" for k, v in sorted(params.items()))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def _mock_generate(self, prompt: str, model_hint: str) -> GenerationResult:
        """Deterministic, dependency-free stand-in for a real model."""
        snippet = prompt.strip().replace("\n", " ")[:140]
        text = (
            "[MOCK] Lokálny LLM model zatiaľ nie je načítaný. Tento režim slúži na "
            "vývoj a testovanie bez GPU/veľkých súborov. Po stiahnutí GGUF modelu "
            "(pozri models/download_and_quantize.sh) sa odpoveď generuje cez llama.cpp.\n\n"
            f"Prijatý prompt ({model_hint}): {snippet}"
        )
        return GenerationResult(
            text=text,
            backend="mock",
            model="mock-0",
            model_hint=model_hint,
            tokens_used=len(text.split()),
            finish_reason="stop",
        )

    # ---- public API ---------------------------------------------------
    def generate(
        self,
        prompt: str,
        *,
        model_hint: str = "7b",
        top_k: int = 40,
        max_tokens: int = 256,
        temperature: float = 0.7,
        use_rag: bool = False,
    ) -> Dict[str, Any]:
        model_hint = model_hint if model_hint in VALID_HINTS else settings.LLM_DEFAULT_HINT

        if use_rag:
            rag_context = _retrieve(prompt, top_k=RAG_MAX_DOCS)
            if rag_context:
                prompt = self._build_rag_prompt(prompt, rag_context)

        cache_key = self._cache_key(
            prompt,
            model_hint=model_hint,
            top_k=top_k,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        with self._lock:
            if cache_key in self._cache:
                logger.debug("LLM cache hit")
                self._cache.move_to_end(cache_key)
                return {**self._cache[cache_key].to_dict(), "cached": True}

            if self.backend == "llama_cpp" and self.model is not None:
                start = time.time()
                out = self.model(
                    prompt, max_tokens=max_tokens, top_k=top_k, temperature=temperature
                )
                elapsed = time.time() - start
                result = GenerationResult(
                    text=out["choices"][0]["text"],
                    backend=self.backend,
                    model=os.path.basename(self.model_path),
                    model_hint=model_hint,
                    tokens_used=int(out.get("usage", {}).get("completion_tokens", 0)),
                    finish_reason=out["choices"][0].get("finish_reason"),
                )
                logger.info(
                    "llama_cpp generated %d tokens in %.2fs", result.tokens_used, elapsed
                )
            else:
                result = self._mock_generate(prompt, model_hint)

            self._cache[cache_key] = result
            # Bounded LRU: an unbounded cache would grow with every unique prompt.
            while len(self._cache) > CACHE_MAX_ENTRIES:
                self._cache.popitem(last=False)
            return result.to_dict()


# Module-level singleton (reloaded per worker in production).
orchestrator = LLMOrchestrator()
