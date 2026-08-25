"""Pydantic request/response schemas for the backend API."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# Allow fields prefixed with `model_` (e.g. model_hint) without warnings.
_CONFIG = ConfigDict(protected_namespaces=())


class LLMPromptRequest(BaseModel):
    model_config = _CONFIG

    prompt: str = Field(..., min_length=1, max_length=16000,
                        description="Text prompt odoslaný lokálnemu modelu.")
    model_hint: str = Field("7b", description="Preferovaná trieda veľkosti modelu: '7b' alebo '3b'.")
    top_k: int = Field(40, ge=0, le=100, description="Počet najlepších tokenov pre vzorkovanie.")
    max_tokens: int = Field(256, ge=1, le=4096, description="Maximálny počet vygenerovaných tokenov.")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Kreativita generovania.")
    use_rag: bool = Field(False, description="Použiť RAG (retrieval) pred generovaním.")


class LLMPromptResponse(BaseModel):
    model_config = _CONFIG
    text: str
    backend: str = Field(..., description="'llama_cpp' alebo 'mock'.")
    model: str
    model_hint: Optional[str] = None
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    cached: bool = False
