def test_ab_sequence_variants(client, auth_headers):
    lead = client.post(
        "/api/leads",
        json={"company_name": "ABCo", "email": "ab@co.sk"},
        headers=auth_headers,
    ).json()
    seq = client.post(
        "/api/sequences",
        json={
            "name": "AB",
            "ab_enabled": True,
            "variants": {
                "A": [{"delay_hours": 1, "subject": "A", "body": "Variant A"}],
                "B": [{"delay_hours": 1, "subject": "B", "body": "Variant B"}],
            },
        },
        headers=auth_headers,
    ).json()
    enr = client.post(
        f"/api/sequences/{seq['id']}/enroll",
        json={"lead_ids": [lead["id"]]},
        headers=auth_headers,
    )
    assert enr.status_code == 200
    report = client.get(f"/api/sequences/{seq['id']}/ab-report", headers=auth_headers).json()
    assert report["total"] == 1
    assert report["A"] + report["B"] == 1

    run = client.post(f"/api/sequences/{seq['id']}/run", headers=auth_headers)
    assert run.status_code == 200
    assert run.json()["sent"] >= 1


def test_ab_report_missing_sequence(client, auth_headers):
    assert client.get("/api/sequences/999999/ab-report", headers=auth_headers).status_code == 404
