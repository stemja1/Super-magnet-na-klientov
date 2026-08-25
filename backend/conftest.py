"""Pytest configuration: isolated temp DB, ORSR mock mode, auth helper."""
import os
import pathlib
import tempfile

# Configure environment BEFORE importing the app (engine is built at import).
_PID = os.getpid()
_DB = pathlib.Path(tempfile.gettempdir()) / f"smk_test_{_PID}.db"
_EMB = pathlib.Path(tempfile.gettempdir()) / f"smk_emb_{_PID}.pkl"
for f in (_DB, _EMB):
    if f.exists():
        f.unlink()
os.environ["DATABASE_URL"] = f"sqlite:///{_DB}"
os.environ["ORSR_MOCK"] = "1"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["EMBEDDINGS_PATH"] = str(_EMB)

import sys

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal, init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()


def _make_user(client: TestClient) -> dict:
    import uuid

    username = f"user_{uuid.uuid4().hex[:10]}"
    password = "password123"
    r = client.post(
        "/api/auth/register",
        json={"username": username, "password": password, "role": "admin"},
    )
    assert r.status_code == 201, r.text
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


import pytest  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db():
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def auth_headers(client):
    return _make_user(client)
