def test_create_and_get_lead(client, auth_headers):
    r = client.post(
        "/api/leads",
        json={"company_name": "Acme s.r.o.", "ico": "12345678", "email": "a@acme.sk"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    lead = r.json()
    assert lead["company_name"] == "Acme s.r.o."
    assert lead["enriched"] == 1  # ORSR mock enriched

    got = client.get(f"/api/leads/{lead['id']}", headers=auth_headers)
    assert got.status_code == 200
    assert got.json()["id"] == lead["id"]


def test_list_leads_filter(client, auth_headers):
    client.post(
        "/api/leads",
        json={"company_name": "FilterCo", "sector": "IT"},
        headers=auth_headers,
    )
    r = client.get("/api/leads?sector=IT", headers=auth_headers)
    assert r.status_code == 200
    assert any(l["company_name"] == "FilterCo" for l in r.json())


def test_update_and_delete_lead(client, auth_headers):
    lead = client.post(
        "/api/leads", json={"company_name": "Temp s.r.o."}, headers=auth_headers
    ).json()
    upd = client.put(
        f"/api/leads/{lead['id']}",
        json={"sector": "FinTech"},
        headers=auth_headers,
    )
    assert upd.status_code == 200
    assert upd.json()["sector"] == "FinTech"

    d = client.delete(f"/api/leads/{lead['id']}", headers=auth_headers)
    assert d.status_code == 200
    assert client.get(f"/api/leads/{lead['id']}", headers=auth_headers).status_code == 404


def test_import_csv(client, auth_headers):
    csv_bytes = (
        b"company_name,ico,email,sector\n"
        b"FirmaA,11111111,a@a.sk,IT\n"
        b"FirmaB,22222222,b@b.sk,Finance\n"
    )
    r = client.post(
        "/api/leads/import",
        files={"file": ("leads.csv", csv_bytes, "text/csv")},
        headers=auth_headers,
    )
    assert r.status_code == 202
    body = r.json()
    assert body["created"] == 2
    assert body["errors"] == []


def test_score_lead_mock(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "ScoreCo", "ico": "999", "email": "x@y.sk", "sector": "IT"},
        headers=auth_headers,
    ).json()
    r = client.post(f"/api/leads/{lead['id']}/score", headers=auth_headers)
    assert r.status_code == 200
    assert 0 <= r.json()["score"] <= 100


def test_lead_not_found(client, auth_headers):
    assert client.get("/api/leads/999999", headers=auth_headers).status_code == 404
