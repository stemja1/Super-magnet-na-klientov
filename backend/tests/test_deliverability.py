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


def test_deliverability_reports_mode_and_optional_selector(client, auth_headers):
    """The module must not crash on typing imports and must expose dkim_selector."""
    r = client.post(
        "/api/email/deliverability",
        json={"domain": "example.com"},
        headers=auth_headers,
    )
    body = r.json()
    assert body["mode"] in ("checked", "unchecked")
    assert "dkim_selector" in body
    # A domain with nothing found cannot claim a perfect score.
    if body["mode"] == "unchecked":
        assert body["score"] == 0


def test_deliverability_evaluates_records_without_dns(monkeypatch):
    """Unit-level: verdict logic is exercised without touching the network."""
    from app.services.email.deliverability import DeliverabilityChecker

    records = {
        "firma.sk": "v=spf1 include:_spf.google.com ~all",
        "_dmarc.firma.sk": "v=DMARC1; p=none",
        "selector1._domainkey.firma.sk": "v=DKIM1; k=rsa; p=abcdef",
    }
    monkeypatch.setattr(
        DeliverabilityChecker, "_txt", lambda self, host: records.get(host)
    )

    ok = DeliverabilityChecker().check("firma.sk")
    assert ok["mode"] == "checked"
    assert ok["spf"] and ok["dmarc"] and ok["dkim_found"]
    assert ok["dkim_selector"] == "selector1"
    assert ok["score"] == 100
    assert ok["issues"] == []


def test_deliverability_flags_missing_records(monkeypatch):
    from app.services.email.deliverability import DeliverabilityChecker

    monkeypatch.setattr(DeliverabilityChecker, "_txt", lambda self, host: None)
    result = DeliverabilityChecker().check("firma.sk")
    assert result["mode"] == "unchecked"
    assert result["score"] == 0
    assert len(result["issues"]) == 3


def test_deliverability_requires_auth(client):
    r = client.post("/api/email/deliverability", json={"domain": "example.com"})
    assert r.status_code in (401, 403)
