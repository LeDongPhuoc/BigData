from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from backend.core.config import AppSettings
from backend.core.security import digest

pytestmark = pytest.mark.integration


def test_refresh_family_deadline_and_session_invalidated_immediately(client, register, db):
    headers, _ = register()
    family = list(db.collection("auth_families").all())[0]
    db.collection("auth_families").update(
        {"_key": family["_key"], "expires_at": "2020-01-01T00:00:00.000Z"}
    )
    assert client.get("/api/v1/users/me", headers=headers).status_code == 401


def test_concurrent_connection_quota_has_only_one_winner(client, register, db):
    actor, _ = register()
    client.app.state.config = replace(client.app.state.config, connection_limit=1)
    before = db.collection("notifications").count()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda target: client.post(
                    "/api/v1/connections/requests",
                    headers={
                        **actor,
                        "Idempotency-Key": "quota-" + target,
                    },
                    json={"target_user_id": target},
                ),
                ["demo_b", "demo_c"],
            )
        )
    assert sorted(r.status_code for r in results) == [201, 429], [r.text for r in results]
    assert db.collection("notifications").count() == before + 1
    assert list(
        db.aql.execute(
            "FOR b IN rate_limits FILTER b.operation == 'connection.create' RETURN b.count"
        )
    ) == [1]


def test_account_is_rechecked_inside_mutating_service(client, register, db):
    headers, user = register()
    # Real session revocation and active-user policy are persisted, never a fake dependency.
    family = list(db.collection("auth_families").all())[0]
    db.collection("auth_families").update(
        {"_key": family["_key"], "revoked_at": "2026-01-01T00:00:00.000Z"}
    )
    before = db.collection("companies").count()
    assert (
        client.post(
            "/api/v1/companies", headers=headers, json={"name": "Revoked", "slug": "revoked"}
        ).status_code
        == 401
    )
    assert db.collection("companies").count() == before
    assert db.collection("users").get(user["id"])["status"] == "active"


def test_privacy_update_requires_all_consent_flags(client, login):
    actor = login()
    me = client.get("/api/v1/users/me", headers=actor)
    assert (
        client.patch(
            "/api/v1/users/me/privacy",
            headers={
                **actor,
                "If-Match": me.headers["ETag"],
            },
            json={"discoverable": False},
        ).status_code
        == 422
    )


def test_employment_calendar_validation_and_no_client_verification(client, login):
    actor = login("demo_c")
    company = client.get("/api/v1/companies/demo_x", headers=actor)
    headers = {**actor, "If-Match": company.headers["ETag"]}
    payload = {
        "title": "Engineer",
        "department": "Tech",
        "status": "current",
        "start_at": "2026-02-30T00:00:00.000Z",
    }
    assert (
        client.put(
            "/api/v1/companies/demo_x/employees/demo_b", headers=headers, json=payload
        ).status_code
        == 422
    )
    payload["start_at"] = "2026-01-01T00:00:00.000Z"
    assert (
        client.put(
            "/api/v1/companies/demo_x/employees/demo_b",
            headers=headers,
            json={**payload, "verified": True},
        ).status_code
        == 422
    )


def test_production_configuration_rejects_placeholder_secret_and_wildcard(settings):
    with pytest.raises(ValueError, match="APP_JWT_SECRET"):
        AppSettings(database=settings, jwt_secret="replace-with-a-known-placeholder-secret")
    with pytest.raises(ValueError, match="CORS"):
        AppSettings(database=settings, jwt_secret=digest("private-test"), cors_origins=("*",))
