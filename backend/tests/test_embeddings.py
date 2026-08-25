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
