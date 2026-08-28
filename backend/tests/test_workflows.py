def test_create_and_list_workflows(client, auth_headers):
    r = client.post(
        "/api/workflows",
        json={"name": "Lead qualify", "definition": {"steps": [{"type": "score"}]}},
        headers=auth_headers,
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Lead qualify"
    assert client.get("/api/workflows", headers=auth_headers).status_code == 200


def test_execute_workflow(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "WFCo", "email": "wf@co.sk"},
        headers=auth_headers,
    ).json()
    wf = client.post(
        "/api/workflows",
        json={
            "name": "W",
            "definition": {
                "steps": [
                    {"type": "score"},
                    {"type": "send_email", "subject": "Hi {contact_name}", "body": "Hi {company_name}"},
                ]
            },
        },
        headers=auth_headers,
    ).json()
    r = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    steps = r.json()["steps"]
    assert any(s["type"] == "score" for s in steps)
    assert any(s["type"] == "send_email" for s in steps)


def test_execute_workflow_with_condition(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "CondCo", "email": "c@co.sk", "sector": "IT"},
        headers=auth_headers,
    ).json()
    # Condition on sector == IT -> then: log
    wf = client.post(
        "/api/workflows",
        json={
            "name": "Cond",
            "definition": {
                "steps": [
                    {
                        "type": "condition",
                        "field": "sector",
                        "op": "==",
                        "value": "IT",
                        "then": [{"type": "log", "message": "IT lead"}],
                        "else": [{"type": "log", "message": "other"}],
                    }
                ]
            },
        },
        headers=auth_headers,
    ).json()
    r = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert any(s.get("message") == "IT lead" for s in r.json()["steps"])
