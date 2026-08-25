def test_create_and_list_sequence(client, auth_headers):
    r = client.post(
        "/api/sequences",
        json={
            "name": "Onboarding",
            "steps": [
                {"delay_hours": 24, "subject": "Ahoj {contact_name}", "body": "Vitaj {company_name}"},
                {"delay_hours": 72, "subject": "Pripomienka", "body": "Pyšte sa {company_name}"},
            ],
        },
        headers=auth_headers,
    )
    assert r.status_code == 201
    seq = r.json()
    assert seq["name"] == "Onboarding"
    assert len(seq["steps"]) == 2

    lst = client.get("/api/sequences", headers=auth_headers)
    assert lst.status_code == 200
    assert any(s["id"] == seq["id"] for s in lst.json())


def test_enroll_and_run_sequence(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "SeqCo", "email": "seq@co.sk", "contact_name": "Jano"},
        headers=auth_headers,
    ).json()

    seq = client.post(
        "/api/sequences",
        json={
            "name": "Cadence",
            "steps": [{"delay_hours": 1, "subject": "Hi {contact_name}", "body": "Hi {company_name}"}],
        },
        headers=auth_headers,
    ).json()

    enr = client.post(
        f"/api/sequences/{seq['id']}/enroll",
        json={"lead_ids": [lead["id"]]},
        headers=auth_headers,
    )
    assert enr.status_code == 200
    assert enr.json()["enrolled"] == 1

    run = client.post(f"/api/sequences/{seq['id']}/run", headers=auth_headers)
    assert run.status_code == 200
    body = run.json()
    assert body["processed"] >= 1
    assert body["sent"] >= 1
