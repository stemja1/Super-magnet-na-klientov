def test_email_status_sandbox(client):
    r = client.get("/api/email/status")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "sandbox"
    assert body["configured"] is False


def test_email_auth_url_requires_config(client):
    # No GMAIL_CLIENT_ID/SECRET in test env -> 400.
    r = client.get("/api/email/auth-url")
    assert r.status_code == 400


def test_send_email_requires_auth(client):
    r = client.post(
        "/api/email/send",
        json={"to": "a@b.sk", "subject": "Hi", "body": "Hello"},
    )
    assert r.status_code in (401, 403)


def test_send_email_sandbox(client, auth_headers):
    r = client.post(
        "/api/email/send",
        json={"to": "a@b.sk", "subject": "Hi", "body": "Hello"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "sandbox"
    assert "message_id" in body
