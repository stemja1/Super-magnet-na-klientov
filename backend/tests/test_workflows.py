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
    body = r.json()
    assert body["status"] == "completed"
    steps = body["steps"]
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


def test_execute_workflow_else_branch(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "NonIT", "email": "n@co.sk", "sector": "Stavebnictvo"},
        headers=auth_headers,
    ).json()
    wf = client.post(
        "/api/workflows",
        json={
            "name": "CondElse",
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
    assert any(s.get("message") == "other" for s in r.json()["steps"])


def test_wait_step_suspends_and_resumes(client, auth_headers):
    """`wait` must be a real suspension: the run stops and a later call continues."""
    lead = client.post(
        "/api/leads",
        json={"company_name": "WaitCo", "email": "w@co.sk"},
        headers=auth_headers,
    ).json()
    wf = client.post(
        "/api/workflows",
        json={
            "name": "WithWait",
            "definition": {
                "steps": [
                    {"type": "log", "message": "before"},
                    {"type": "wait", "hours": 0},
                    {"type": "log", "message": "after"},
                ]
            },
        },
        headers=auth_headers,
    ).json()

    first = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    ).json()
    assert first["status"] == "waiting"
    assert [s.get("message") for s in first["steps"]] == ["before", "wait"] or any(
        s["type"] == "wait" for s in first["steps"]
    )
    assert not any(s.get("message") == "after" for s in first["steps"])

    # hours=0 makes the resume immediately due.
    second = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    ).json()
    assert second["status"] == "completed"
    assert any(s.get("message") == "after" for s in second["steps"])
    # "before" must not run twice.
    assert not any(s.get("message") == "before" for s in second["steps"])


def test_wait_respects_future_resume_time(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "FutureCo", "email": "f@co.sk"},
        headers=auth_headers,
    ).json()
    wf = client.post(
        "/api/workflows",
        json={
            "name": "FutureWait",
            "definition": {
                "steps": [
                    {"type": "wait", "hours": 48},
                    {"type": "log", "message": "later"},
                ]
            },
        },
        headers=auth_headers,
    ).json()

    client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    )
    # Not yet due: the run restarts from the top and suspends again.
    again = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    ).json()
    assert again["status"] == "waiting"
    assert not any(s.get("message") == "later" for s in again["steps"])


def test_unknown_step_type_is_reported_not_fatal(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "UnknownCo", "email": "u@co.sk"},
        headers=auth_headers,
    ).json()
    wf = client.post(
        "/api/workflows",
        json={
            "name": "Unknown",
            "definition": {
                "steps": [{"type": "teleport"}, {"type": "log", "message": "done"}]
            },
        },
        headers=auth_headers,
    ).json()
    r = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    ).json()
    assert r["status"] == "completed"
    assert any(s.get("skipped") == "unsupported step type" for s in r["steps"])
    assert any(s.get("message") == "done" for s in r["steps"])


def test_oversized_definition_rejected(client, auth_headers):
    steps = [{"type": "log", "message": "x"} for _ in range(101)]
    r = client.post(
        "/api/workflows",
        json={"name": "TooBig", "definition": {"steps": steps}},
        headers=auth_headers,
    )
    assert r.status_code == 422


def test_deeply_nested_conditions_do_not_recurse_forever(client, auth_headers):
    definition = {"steps": [{"type": "log", "message": "leaf"}]}
    for _ in range(30):
        definition = {
            "steps": [
                {"type": "condition", "field": "sector", "op": "==", "value": "IT",
                 "then": definition["steps"]}
            ]
        }
    lead = client.post(
        "/api/leads",
        json={"company_name": "DeepCo", "email": "d@co.sk", "sector": "IT"},
        headers=auth_headers,
    ).json()
    wf = client.post(
        "/api/workflows",
        json={"name": "Deep", "definition": definition},
        headers=auth_headers,
    ).json()
    r = client.post(
        "/api/workflows/execute",
        json={"workflow_id": wf["id"], "lead_id": lead["id"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
