def test_deliverability_check(client, auth_headers):
    r = client.post(
        "/api/email/deliverability",
        json={"domain": "example.com"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    for key in ("spf", "dmarc", "dkim_found", "score", "issues", "mode"):
        assert key in body


def test_deliverability_requires_auth(client):
    r = client.post("/api/email/deliverability", json={"domain": "example.com"})
    assert r.status_code in (401, 403)
