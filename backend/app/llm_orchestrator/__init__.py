"""LLM orchestrator package (layout alias of services.llm_orchestrator).

Kept as a dedicated package so later sprints can add prompt templates,
RAG retrieval, and token-window management next to the orchestrator.
"""
from app.services.llm_orchestrator import (
    LLMOrchestrator,
    orchestrator,
    register_rag_documents,
)

__all__ = ["LLMOrchestrator", "orchestrator", "register_rag_documents"]
