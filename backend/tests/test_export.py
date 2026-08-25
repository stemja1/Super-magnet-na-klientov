def test_csv_export(client, auth_headers):
    client.post(
        "/api/leads",
        json={"company_name": "ExportCo", "email": "exp@co.sk"},
        headers=auth_headers,
    )
    r = client.get("/api/export/leads.csv", headers=auth_headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "ExportCo" in r.text


def test_google_sheets_export_sandbox(client, auth_headers):
    r = client.post(
        "/api/export/google-sheets",
        json={"spreadsheet_id": "fake-id"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "simulated"


def test_google_docs_export_sandbox(client, auth_headers):
    r = client.post(
        "/api/export/google-docs",
        json={"title": "Lead report"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "simulated"
    assert "documentId" in r.json()
