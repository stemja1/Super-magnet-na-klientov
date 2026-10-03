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


def test_oauth_callback_rejects_unknown_state(client, monkeypatch):
    """CSRF guard: a callback with a state we never issued must be refused."""
    from app.api import email as email_api

    monkeypatch.setattr(email_api, "get_client", lambda: _FakeClient())
    r = client.get("/api/email/callback", params={"code": "x", "state": "forged"})
    assert r.status_code == 400


def test_oauth_callback_accepts_issued_state_once(client, monkeypatch):
    from app.api import email as email_api

    fake = _FakeClient()
    _, state = fake.client.get_auth_url()
    monkeypatch.setattr(email_api, "get_client", lambda: fake)

    ok = client.get("/api/email/callback", params={"code": "x", "state": state})
    assert ok.status_code == 200
    assert fake.exchanged == ["x"]
    # Replaying the same state must fail.
    replay = client.get("/api/email/callback", params={"code": "x", "state": state})
    assert replay.status_code == 400
    assert fake.exchanged == ["x"]


class _FakeClient:
    def __init__(self):
        from app.services.integrations.google_oauth import GoogleOAuthClient

        self.client = GoogleOAuthClient("id", "secret", "http://localhost/cb", "s")
        self.exchanged: list[str] = []

    def is_configured(self) -> bool:
        return True

    def mode(self) -> str:
        return "sandbox"

    def get_auth_url(self, state=None):
        return self.client.get_auth_url(state)

    def consume_state(self, state: str) -> bool:
        return self.client.consume_state(state)

    def exchange_code(self, code: str) -> None:
        self.exchanged.append(code)


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
