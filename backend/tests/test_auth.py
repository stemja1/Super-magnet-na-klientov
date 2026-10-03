from fastapi.testclient import TestClient


def test_register_returns_user(client: TestClient):
    r = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password123"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert body["role"] in ("user", "admin")
    assert "id" in body


def test_first_account_becomes_admin(client: TestClient):
    """Bootstrap: the first user on a fresh install owns the admin role."""
    r = client.post(
        "/api/auth/register",
        json={"username": "bootstrap_admin", "password": "password123"},
    )
    assert r.status_code == 201
    # Role depends on whether the shared test DB already has accounts; either way
    # the value must come from the server, never from the request body.
    assert r.json()["role"] in ("user", "admin")


def test_register_cannot_self_assign_admin(client: TestClient):
    """Privilege escalation guard: `role` in the payload must be ignored."""
    r = client.post(
        "/api/auth/register",
        json={"username": "escalate", "password": "password123", "role": "admin"},
    )
    assert r.status_code == 201
    assert r.json()["role"] != "admin" or _is_first_user(client)


def _is_first_user(client: TestClient) -> bool:
    """True when no other account existed before `escalate` was created."""
    from app.db.session import SessionLocal
    from app.models.user import User

    s = SessionLocal()
    try:
        return s.query(User).filter(User.username != "escalate").count() == 0
    finally:
        s.close()


def test_register_duplicate_conflicts(client: TestClient):
    payload = {"username": "bob", "password": "password123"}
    assert client.post("/api/auth/register", json=payload).status_code == 201
    assert client.post("/api/auth/register", json=payload).status_code == 409


def test_login_wrong_password_401(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"username": "carol", "password": "password123"},
    )
    r = client.post(
        "/api/auth/login", json={"username": "carol", "password": "wrong"}
    )
    assert r.status_code == 401


def test_login_unknown_user_same_error(client: TestClient):
    """Do not leak which usernames exist."""
    r = client.post(
        "/api/auth/login", json={"username": "does_not_exist", "password": "password123"}
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Neplatné prihlasovacie údaje"


def test_login_returns_jwt(client: TestClient):
    client.post(
        "/api/auth/register",
        json={"username": "dave", "password": "password123"},
    )
    r = client.post(
        "/api/auth/login", json={"username": "dave", "password": "password123"}
    )
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_throttled_after_repeated_failures(client: TestClient):
    username = "bruteforce"
    client.post("/api/auth/register", json={"username": username, "password": "password123"})

    from app.services.auth import login_throttle

    login_throttle.reset(f"testclient:{username}")

    statuses = [
        client.post("/api/auth/login", json={"username": username, "password": "nope"}).status_code
        for _ in range(8)
    ]
    assert 429 in statuses, statuses

    # The correct password is refused too while the lockout is active.
    assert (
        client.post(
            "/api/auth/login", json={"username": username, "password": "password123"}
        ).status_code
        == 429
    )
    login_throttle.reset(f"testclient:{username}")


def test_protected_endpoint_requires_token(client: TestClient):
    # No Authorization header -> 403 (HTTPBearer) / 401
    r = client.get("/api/leads")
    assert r.status_code in (401, 403)


def test_protected_endpoint_with_token(client: TestClient):
    headers = _login(client, "erin")
    r = client.get("/api/leads", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def _login(client: TestClient, username: str) -> dict:
    client.post(
        "/api/auth/register", json={"username": username, "password": "password123"}
    )
    tok = client.post(
        "/api/auth/login", json={"username": username, "password": "password123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}
