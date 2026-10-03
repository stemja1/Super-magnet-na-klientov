"""LLM orchestrator package (layout alias of services.llm_orchestrator).

Kept as a dedicated package so later sprints can add prompt templates,
RAG retrieval, and token-window management next to the orchestrator.

RAG documents live in the shared vector store (``app.services.embeddings.store``)
and are added via ``POST /api/embeddings/upsert``; there is no separate in-memory
corpus to seed.
"""
from app.services.llm_orchestrator import LLMOrchestrator, orchestrator

__all__ = ["LLMOrchestrator", "orchestrator"]
