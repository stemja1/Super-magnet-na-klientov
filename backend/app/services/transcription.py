"""Transcription service (spec §3): whisper.cpp wrapper with sandbox fallback.

Tries the local `whisper-cli` (whisper.cpp) when available; otherwise returns a
simulated transcript so the pipeline is runnable offline. Call insights are
produced by the LLM Orchestrator using the call-summarization prompt template.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import uuid

from app.llm_orchestrator.prompts import CALL_SUMMARIZATION_TEMPLATE
from app.services.llm_orchestrator import orchestrator


class TranscriptionService:
    def transcribe(self, audio_path: str) -> dict:
        cli = os.getenv("WHISPER_CLI", "whisper-cli")
        model = os.getenv("WHISPER_MODEL", "")
        if model and os.path.exists(model):
            try:
                out_dir = tempfile.mkdtemp()
                subprocess.run(
                    [cli, "-f", audio_path, "-m", model, "-otxt", "-of", "out", "-o", out_dir],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                txt = os.path.join(out_dir, "out.txt")
                if os.path.exists(txt):
                    with open(txt, encoding="utf-8") as f:
                        return {"text": f.read().strip(), "mode": "live"}
            except Exception:
                pass
        return {
            "text": "[SANDBOX] Simulovaný prepis obchodného hovoru: zákazník má záujem o produkt, čaká na cenovú ponuku.",
            "mode": "sandbox",
        }

    def insights(self, transcript: str) -> dict:
        prompt = CALL_SUMMARIZATION_TEMPLATE.format(transcript=transcript)
        if orchestrator.backend == "mock":
            return {
                "summary": "[SANDBOX] Hlavný záujem: cenová ponuka. Ďalší krok: zaslať ponuku do 2 dní. Odhad konverzie: 70%.",
                "mode": "mock",
            }
        res = orchestrator.generate(prompt, model_hint="7b", max_tokens=300, temperature=0.3)
        return {"summary": res.get("text", ""), "mode": "llm"}
