"""Integration/unit tests for the LLM API endpoint.

These run without any model weights: the orchestrator transparently uses its
mock backend, so CI works on machines without a GPU or large downloads.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert "llm_backend" in body


def test_root_links():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["docs"] == "/docs"


def test_llm_prompt_returns_text():
    r = client.post("/api/llm/prompt", json={"prompt": "Ahoj, ako sa máš?"})
    assert r.status_code == 200
    body = r.json()
    assert body["text"]
    assert body["backend"] in ("mock", "llama_cpp")
    assert body["model_hint"] == "7b"


def test_llm_prompt_defaults_and_rag_flag():
    r = client.post("/api/llm/prompt", json={"prompt": "Skóre leadu", "use_rag": True})
    assert r.status_code == 200
    assert "backend" in r.json()


def test_llm_prompt_rejects_empty_prompt():
    r = client.post("/api/llm/prompt", json={"prompt": ""})
    assert r.status_code == 422


def test_llm_prompt_rejects_bad_max_tokens():
    r = client.post("/api/llm/prompt", json={"prompt": "x", "max_tokens": 99999})
    assert r.status_code == 422


def test_llm_status_endpoint():
    r = client.get("/api/llm/status")
    assert r.status_code == 200
    assert "backend" in r.json()
