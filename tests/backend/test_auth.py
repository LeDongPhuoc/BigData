from concurrent.futures import ThreadPoolExecutor

import jwt
import pytest

from backend.core.security import verify_password

pytestmark = pytest.mark.integration
PASSWORD = "Integration passphrase 2026!"


def test_register_persists_hash_and_rejects_role_injection(client, db):
    payload = {"email": "NEW@Example.com", "password": PASSWORD, "display_name": " New "}
    invalid = client.post("/api/v1/auth/register", json={**payload, "roles": ["admin"]})
    assert invalid.status_code == 422
    result = client.post("/api/v1/auth/register", json=payload)
    assert result.status_code == 201, result.text
    tokens = result.json()
    me = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer " + tokens["access_token"],
        },
    )
    assert me.status_code == 200, me.text
    user = me.json()
    assert user["email"] == "new@example.com" and user["roles"] == ["candidate"]
    credentials = list(db.collection("auth_credentials").all())
    assert len(credentials) == 1
    assert credentials[0]["password_hash"].startswith("$argon2id$")
    assert verify_password(credentials[0]["password_hash"], PASSWORD)
    session = list(db.collection("auth_sessions").all())[0]
    assert tokens["refresh_token"] not in str(session)
    assert "password" not in me.text and "session_id" not in user
    assert client.post("/api/v1/auth/register", json=payload).status_code == 409


def test_refresh_rotation_reuse_revokes_entire_family(client, register):
    headers, user = register()
    login = client.post("/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD})
    original = login.json()
    rotated = client.post("/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]})
    assert rotated.status_code == 200, rotated.text
    assert rotated.json()["refresh_token"] != original["refresh_token"]
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": original["refresh_token"],
            },
        ).status_code
        == 401
    )
    assert (
        client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": "Bearer " + rotated.json()["access_token"],
            },
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": rotated.json()["refresh_token"],
            },
        ).status_code
        == 401
    )
    # A different login family remains valid.
    assert client.get("/api/v1/users/me", headers=headers).status_code == 200


def test_logout_and_tampered_jwt(client, login):
    headers = login()
    invalid = {"Authorization": headers["Authorization"] + "tampered"}
    assert client.get("/api/v1/auth/me", headers=invalid).status_code == 401
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.get("/api/v1/auth/me").status_code == 401


def test_concurrent_registration_unique_email(client, db):
    payload = {"email": "race@example.com", "password": PASSWORD, "display_name": "Race"}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(lambda _: client.post("/api/v1/auth/register", json=payload), range(2))
        )
    assert sorted(r.status_code for r in results) == [201, 409]
    assert db.collection("auth_credentials").count() == 1
    assert db.collection("auth_families").count() == 1


def test_login_throttle_persisted_and_validation_has_no_password(client, db):
    payload = {"email": "unknown@example.com", "password": PASSWORD}
    for _ in range(10):
        assert client.post("/api/v1/auth/login", json=payload).status_code == 401
    limited = client.post("/api/v1/auth/login", json=payload)
    assert limited.status_code == 429
    assert db.collection("rate_limits").count() == 1
    invalid = client.post("/api/v1/auth/register", json={**payload, "password": "secret"})
    assert invalid.status_code == 422
    assert "secret" not in invalid.text and "input" not in invalid.text
    assert invalid.json()["error"]["request_id"] == invalid.headers["X-Request-ID"]


def test_expired_tokens_refresh_hash_mismatch_and_suspended_user(client, register, db, api_config):
    headers, user = register()
    raw = headers["Authorization"].split()[1]
    claims = jwt.decode(raw, options={"verify_signature": False})
    claims["exp"] = 1
    expired = jwt.encode(claims, api_config.jwt_secret, algorithm="HS256")
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer " + expired,
            },
        ).status_code
        == 401
    )
    result = client.post("/api/v1/auth/login", json={"email": user["email"], "password": PASSWORD})
    refresh = result.json()["refresh_token"]
    assert (
        client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": refresh.split(".")[0] + "." + "x" * 64,
            },
        ).status_code
        == 401
    )
    assert client.post("/api/v1/auth/refresh", json={"refresh_token": refresh}).status_code == 200
    db.collection("users").update({"_key": user["id"], "status": "suspended"})
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_refresh_race_revokes_winning_token_on_reuse(client, register):
    _, user = register()
    original = client.post(
        "/api/v1/auth/login",
        json={
            "email": user["email"],
            "password": PASSWORD,
        },
    ).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda _: client.post(
                    "/api/v1/auth/refresh",
                    json={
                        "refresh_token": original["refresh_token"],
                    },
                ),
                range(2),
            )
        )
    assert sorted(r.status_code for r in results) == [200, 401]
    winner = next(r for r in results if r.status_code == 200)
    assert (
        client.get(
            "/api/v1/auth/me",
            headers={
                "Authorization": "Bearer " + winner.json()["access_token"],
            },
        ).status_code
        == 401
    )
