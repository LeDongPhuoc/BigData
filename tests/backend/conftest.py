import secrets
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.config import AppSettings
from backend.core.security import hash_password
from backend.modules.auth.repository import AuthRepository

PASSWORD = "Integration passphrase 2026!"


@pytest.fixture(scope="session")
def password_hash():
    return hash_password(PASSWORD)


@pytest.fixture
def api_config(settings):
    return AppSettings(database=settings, jwt_secret=secrets.token_urlsafe(48))


@pytest.fixture
def client(db, api_config):
    with TestClient(
        create_app(
            replace(
                api_config,
                database=replace(
                    api_config.database,
                    database=db.name,
                ),
            ),
            db=db,
        )
    ) as client:
        yield client


@pytest.fixture
def login(client, db, password_hash):
    def authenticate(user_key="demo_a", *, admin=False):
        user = db.collection("users").get(user_key)
        if admin:
            db.collection("users").update({"_key": user_key, "roles": ["admin"]})
        repo = AuthRepository(db)
        if not repo.credential(user["_id"]):
            repo.insert({"user_id": user["_id"], "password_hash": password_hash})
        result = client.post(
            "/api/v1/auth/login",
            json={
                "email": user["email"],
                "password": PASSWORD,
            },
        )
        assert result.status_code == 200, result.text
        return {"Authorization": "Bearer " + result.json()["access_token"]}

    return authenticate


@pytest.fixture
def register(client):
    def create():
        email = uuid4().hex + "@example.com"
        result = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": PASSWORD,
                "display_name": "Integration User",
            },
        )
        assert result.status_code == 201, result.text
        headers = {"Authorization": "Bearer " + result.json()["access_token"]}
        user = client.get("/api/v1/users/me", headers=headers).json()
        return headers, user

    return create


@pytest.fixture
def reachable(client, register, login):
    candidate, user = register()
    bridge = login("demo_b")
    referrer = login("demo_c")
    request = client.post(
        "/api/v1/connections/requests",
        headers={
            **candidate,
            "Idempotency-Key": "bridge",
        },
        json={"target_user_id": "demo_b"},
    )
    assert request.status_code == 201, request.text
    accepted = client.post(
        "/api/v1/connections/" + request.json()["id"] + "/accept",
        headers={**bridge, "If-Match": request.headers["ETag"]},
    )
    assert accepted.status_code == 200, accepted.text
    return candidate, user, referrer
