import pytest

pytestmark = pytest.mark.integration


def test_audit_read_requires_admin_and_request_ids_are_correlated(client, login):
    candidate = login()
    admin = login("demo_x", admin=True)
    assert client.get("/api/v1/admin/audit", headers=candidate).status_code == 403
    me = client.get("/api/v1/users/me", headers=candidate)
    result = client.patch(
        "/api/v1/users/me",
        headers={
            **candidate,
            "If-Match": me.headers["ETag"],
            "X-Request-ID": "audit-correlation-test",
        },
        json={"display_name": "Audit sample"},
    )
    assert result.status_code == 200
    rows = client.get("/api/v1/admin/audit", headers=admin).json()["items"]
    row = next(r for r in rows if r["request_id"] == "audit-correlation-test")
    assert row["action"] == "user.profile" and row["actor_id"] == "users/demo_a"
    assert row["metadata"] == {"status": None, "reason": None}
    assert "Authorization" not in str(rows) and "password_hash" not in str(rows)
