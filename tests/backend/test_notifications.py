import pytest

pytestmark = pytest.mark.integration


def test_notification_recipient_only_read_with_revision(client, register, db):
    inviter, _ = register()
    recipient, user = register()
    assert (
        client.post(
            "/api/v1/connections/requests",
            headers={
                **inviter,
                "Idempotency-Key": "notification",
            },
            json={"target_user_id": user["id"]},
        ).status_code
        == 201
    )
    notifications = client.get("/api/v1/notifications/me", headers=recipient)
    assert notifications.status_code == 200
    item = notifications.json()["items"][0]
    assert "event_key" not in item and "recipient_id" not in item
    headers = {"If-Match": '"' + item["revision"] + '"'}
    route = "/api/v1/notifications/" + item["id"] + "/read"
    assert client.post(route, headers={**inviter, **headers}).status_code == 404
    read = client.post(route, headers={**recipient, **headers})
    assert read.status_code == 200 and read.json()["read_at"]
    assert client.post(route, headers={**recipient, **headers}).status_code == 412
    assert db.collection("notifications").get(item["id"])["read_at"] == read.json()["read_at"]
