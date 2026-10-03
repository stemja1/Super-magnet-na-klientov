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


def test_enroll_is_idempotent(client, auth_headers):
    """A retried enroll request must not create duplicate email deliveries."""
    lead = client.post(
        "/api/leads",
        json={"company_name": "DupCo", "email": "dup@co.sk"},
        headers=auth_headers,
    ).json()
    seq = client.post(
        "/api/sequences",
        json={
            "name": "Idempotent",
            "steps": [{"delay_hours": 1, "subject": "Hi", "body": "Hi"}],
        },
        headers=auth_headers,
    ).json()

    first = client.post(
        f"/api/sequences/{seq['id']}/enroll",
        json={"lead_ids": [lead["id"]]},
        headers=auth_headers,
    ).json()
    assert first["enrolled"] == 1

    second = client.post(
        f"/api/sequences/{seq['id']}/enroll",
        json={"lead_ids": [lead["id"]]},
        headers=auth_headers,
    ).json()
    assert second["enrolled"] == 0
    assert second["skipped_duplicates"] == 1

    # Only one email goes out, not two.
    run = client.post(f"/api/sequences/{seq['id']}/run", headers=auth_headers).json()
    assert run["sent"] == 1


def test_run_due_isolates_failures(client, auth_headers):
    """One failing send must not abort the whole batch."""
    from app.services import sequences as seq_svc

    good = client.post(
        "/api/leads",
        json={"company_name": "GoodCo", "email": "good@co.sk"},
        headers=auth_headers,
    ).json()
    bad = client.post(
        "/api/leads",
        json={"company_name": "BadCo", "email": "bad@co.sk"},
        headers=auth_headers,
    ).json()
    seq = client.post(
        "/api/sequences",
        json={
            "name": "Failure isolation",
            "steps": [{"delay_hours": 1, "subject": "Hi", "body": "Hi"}],
        },
        headers=auth_headers,
    ).json()
    for lead_id in (bad["id"], good["id"]):
        client.post(
            f"/api/sequences/{seq['id']}/enroll",
            json={"lead_ids": [lead_id]},
            headers=auth_headers,
        )

    class FlakyConnector:
        def send_email(self, to, subject, body):
            if to == "bad@co.sk":
                raise RuntimeError("SMTP down")
            return {"message_id": "ok-1", "mode": "sandbox"}

    from app.db.session import SessionLocal

    session = SessionLocal()
    try:
        result = seq_svc.run_due(session, sequence_id=seq["id"], connector=FlakyConnector())
    finally:
        session.close()

    assert result["sent"] == 1
    assert result["failed"] == 1


def test_render_only_substitutes_known_slots():
    from app.models.lead import Lead
    from app.services.sequences import _render

    lead = Lead(company_name="Acme s.r.o.", contact_name="Jano", ico="123", sector="IT")
    assert _render("Vitaj {contact_name} z {company_name}", lead) == "Vitaj Jano z Acme s.r.o."
    # Unknown / malformed placeholders are left as-is instead of raising.
    assert _render("Pozor: {unknown} {0}", lead) == "Pozor: {unknown} {0}"
    assert _render("", lead) == ""
