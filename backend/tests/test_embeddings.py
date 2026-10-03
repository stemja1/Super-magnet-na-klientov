def test_upsert_and_search(client, auth_headers):
    client.post(
        "/api/embeddings/upsert",
        json={
            "doc_id": "d1",
            "text": "Lead scoring pre IT firmu na Slovensku",
            "metadata": {"type": "note"},
        },
        headers=auth_headers,
    )
    client.post(
        "/api/embeddings/upsert",
        json={
            "doc_id": "d2",
            "text": "Schôdzka s klientom o logistike",
            "metadata": {"type": "note"},
        },
        headers=auth_headers,
    )
    r = client.get(
        "/api/embeddings/search", params={"q": "IT firma Slovensko", "top_k": 2},
        headers=auth_headers,
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) >= 1
    assert results[0]["id"] == "d1"


def test_search_requires_query(client, auth_headers):
    r = client.get("/api/embeddings/search", headers=auth_headers)
    assert r.status_code == 422


def test_search_blank_query_returns_400(client, auth_headers):
    """Whitespace passes min_length=1, so the explicit blank check must fire."""
    r = client.get(
        "/api/embeddings/search", params={"q": "   "}, headers=auth_headers
    )
    assert r.status_code == 400


def test_upsert_is_idempotent_per_doc_id(client, auth_headers):
    """Re-upserting the same id must replace, not duplicate."""
    first = client.post(
        "/api/embeddings/upsert",
        json={"doc_id": "dup", "text": "prvá verzia", "metadata": {"v": 1}},
        headers=auth_headers,
    ).json()
    assert first["inserted"] == 1
    assert first["updated"] == 0

    before = client.get("/api/embeddings/info", headers=auth_headers).json()["documents"]

    second = client.post(
        "/api/embeddings/upsert",
        json={"doc_id": "dup", "text": "druhá verzia", "metadata": {"v": 2}},
        headers=auth_headers,
    ).json()
    assert second["inserted"] == 0
    assert second["updated"] == 1

    after = client.get("/api/embeddings/info", headers=auth_headers).json()["documents"]
    assert after == before

    hits = client.get(
        "/api/embeddings/search", params={"q": "druhá verzia", "top_k": 5},
        headers=auth_headers,
    ).json()["results"]
    matching = [h for h in hits if h["id"] == "dup"]
    assert len(matching) == 1
    assert matching[0]["metadata"]["v"] == 2


def test_delete_document(client, auth_headers):
    client.post(
        "/api/embeddings/upsert",
        json={"doc_id": "tmp", "text": "na zmazanie", "metadata": {}},
        headers=auth_headers,
    )
    r = client.delete("/api/embeddings/tmp", headers=auth_headers)
    assert r.status_code == 200
    assert client.delete("/api/embeddings/tmp", headers=auth_headers).status_code == 404

    hits = client.get(
        "/api/embeddings/search", params={"q": "na zmazanie", "top_k": 5},
        headers=auth_headers,
    ).json()["results"]
    assert not [h for h in hits if h["id"] == "tmp"]


def test_info_reports_backend(client, auth_headers):
    r = client.get("/api/embeddings/info", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["backend"] in ("sentence-transformers", "hashing")
    assert isinstance(body["semantic"], bool)
    assert body["dim"] > 0


def test_rag_retrieval_uses_vector_store(client, auth_headers):
    """`use_rag` must actually pull context out of the embeddings store."""
    from app.services.llm_orchestrator import _retrieve

    client.post(
        "/api/embeddings/upsert",
        json={
            "doc_id": "rag-doc",
            "text": "Lead scoring pre slovenskú IT firmu",
            "metadata": {"text": "Lead scoring pre slovenskú IT firmu"},
        },
        headers=auth_headers,
    )
    hits = _retrieve("slovenská IT firma", top_k=3)
    assert any("IT firmu" in h for h in hits)
