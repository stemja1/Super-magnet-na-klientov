from fastapi.testclient import TestClient


def test_register_returns_user(client: TestClient):
    r = client.post(
        "/api/auth/register",
        json={"username": "alice", "password": "password123", "role": "admin"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert body["role"] == "admin"
    assert "id" in body


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
