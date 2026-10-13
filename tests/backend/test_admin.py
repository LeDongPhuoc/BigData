import pytest

pytestmark = pytest.mark.integration


def test_moderation_revokes_sessions_and_audits(client, login, register, db):
    actor, user = register()
    admin = login("demo_x", admin=True)
    route = "/api/v1/admin/users/" + user["id"] + "/status"
    supplied = '"' + user["revision"] + '"'
    payload = {"status": "suspended", "reason": "spam investigation"}
    assert (
        client.patch(route, headers={**actor, "If-Match": supplied}, json=payload).status_code
        == 403
    )
    moderated = client.patch(route, headers={**admin, "If-Match": supplied}, json=payload)
    assert moderated.status_code == 200, moderated.text
    assert client.get("/api/v1/auth/me", headers=actor).status_code == 401
    restored = client.patch(
        route,
        headers={**admin, "If-Match": moderated.headers["ETag"]},
        json={"status": "active", "reason": "resolved"},
    )
    assert restored.status_code == 200
    # Restoration never revives the old login family.
    assert client.get("/api/v1/auth/me", headers=actor).status_code == 401
    families = list(
        db.aql.execute(
            "FOR f IN auth_families FILTER f.user_id == @user RETURN f",
            bind_vars={"user": "users/" + user["id"]},
        )
    )
    assert all(f["revoked_at"] for f in families)


def test_admin_accounts_protected_and_deleted_users_not_restored(client, register, login):
    _, user = register()
    admin = login("demo_x", admin=True)
    current = client.get("/api/v1/users/me", headers=admin)
    assert (
        client.patch(
            "/api/v1/admin/users/demo_x/status",
            headers={
                **admin,
                "If-Match": current.headers["ETag"],
            },
            json={"status": "deleted", "reason": "self"},
        ).status_code
        == 403
    )
    route = "/api/v1/admin/users/" + user["id"] + "/status"
    deleted = client.patch(
        route,
        headers={**admin, "If-Match": '"' + user["revision"] + '"'},
        json={"status": "deleted", "reason": "requested"},
    )
    assert deleted.status_code == 200 and deleted.json()["deleted_at"]
    assert (
        client.patch(
            route,
            headers={**admin, "If-Match": deleted.headers["ETag"]},
            json={"status": "active", "reason": "restore"},
        ).status_code
        == 409
    )
