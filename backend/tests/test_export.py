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


def test_csv_export_neutralizes_formula_injection(client, auth_headers):
    """A lead named '=cmd|...' must not execute when the CSV is opened in Excel."""
    client.post(
        "/api/leads",
        json={"company_name": "=cmd|'/c calc'!A1", "notes": "@SUM(A1)"},
        headers=auth_headers,
    )
    r = client.get("/api/export/leads.csv", headers=auth_headers)
    assert r.status_code == 200
    assert "'=cmd|" in r.text
    assert "@SUM" not in r.text.replace("'@SUM", "")


def test_sanitize_csv_cell():
    from app.api.export import sanitize_csv_cell

    assert sanitize_csv_cell("=1+1") == "'=1+1"
    assert sanitize_csv_cell("+41") == "'+41"
    assert sanitize_csv_cell("-5") == "'-5"
    assert sanitize_csv_cell("@evil") == "'@evil"
    assert sanitize_csv_cell("Acme s.r.o.") == "Acme s.r.o."
    assert sanitize_csv_cell(None) == ""


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
