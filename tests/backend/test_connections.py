from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.integration


def create(client, inviter, target, token="connection-request"):
    return client.post(
        "/api/v1/connections/requests",
        headers={
            **inviter,
            "Idempotency-Key": token,
        },
        json={"target_user_id": target},
    )


def test_connection_workflow_idor_etag_block_cannot_be_deleted(client, register, db):
    a, alice = register()
    b, bob = register()
    outsider, _ = register()
    result = create(client, a, bob["id"])
    assert result.status_code == 201, result.text
    connection = result.json()
    assert connection["status"] == "pending" and connection["trust"] is None
    stored = db.collection("connections").get(connection["id"])
    assert stored["_from"] < stored["_to"]
    assert stored["pair_key"] == stored["_from"] + "|" + stored["_to"]
    route = "/api/v1/connections/" + connection["id"]
    assert client.get(route, headers=outsider).status_code == 404
    assert (
        client.post(
            route + "/accept", headers={**a, "If-Match": result.headers["ETag"]}
        ).status_code
        == 403
    )
    inbox = client.get("/api/v1/connections/requests/incoming", headers=b).json()["items"]
    assert connection["id"] in {c["id"] for c in inbox}
    accepted = client.post(route + "/accept", headers={**b, "If-Match": result.headers["ETag"]})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted_at"]
    assert (
        client.post(
            route + "/reject", headers={**b, "If-Match": result.headers["ETag"]}
        ).status_code
        == 412
    )
    assert client.get("/api/v1/graph/connections", headers=a).json()["items"][0]["id"] == bob["id"]
    blocked = client.post(route + "/block", headers={**a, "If-Match": accepted.headers["ETag"]})
    assert blocked.status_code == 200
    assert (
        client.delete(route, headers={**b, "If-Match": blocked.headers["ETag"]}).status_code == 409
    )
    assert client.get("/api/v1/users/" + alice["id"] + "/profile", headers=b).status_code == 404
    assert client.get("/api/v1/graph/connections", headers=a).json()["items"] == []


def test_connection_replay_payload_conflict_and_unique_pair(client, register, db):
    a, alice = register()
    b, bob = register()
    before = db.collection("notifications").count()
    first = create(client, a, bob["id"])
    replay = create(client, a, bob["id"])
    assert first.status_code == 201 and replay.status_code == 200
    assert first.json()["id"] == replay.json()["id"]
    assert db.collection("notifications").count() == before + 1
    assert create(client, a, "demo_b").status_code == 409
    assert create(client, b, alice["id"], "reverse").status_code == 409
    assert create(client, a, alice["id"], "self").status_code == 422
    assert (
        client.post(
            "/api/v1/connections/requests", headers=a, json={"target_user_id": bob["id"]}
        ).status_code
        == 422
    )


def test_concurrent_idempotent_connection_creates_one_notification(client, register, db):
    actor, _ = register()
    _, target = register()
    before = db.collection("notifications").count()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: create(client, actor, target["id"], "race"), range(4)))
    assert sorted(r.status_code for r in results) == [200, 200, 200, 201]
    assert len({r.json()["id"] for r in results}) == 1
    assert db.collection("notifications").count() == before + 1


def test_reject_and_soft_delete_keep_pair_history(client, register, db):
    actor, _ = register()
    target, user = register()
    created = create(client, actor, user["id"])
    route = "/api/v1/connections/" + created.json()["id"]
    rejected = client.post(
        route + "/reject", headers={**target, "If-Match": created.headers["ETag"]}
    )
    assert rejected.status_code == 200 and rejected.json()["status"] == "rejected"
    assert (
        client.delete(route, headers={**actor, "If-Match": rejected.headers["ETag"]}).status_code
        == 204
    )
    assert db.collection("connections").get(created.json()["id"])["deleted_at"]
    assert create(client, actor, user["id"], "retry").status_code == 409


def test_connection_quota_atomic_and_replays_do_not_consume(client, register, db):
    actor, _ = register()
    client.app.state.config = __import__("dataclasses").replace(
        client.app.state.config, connection_limit=1
    )
    first = create(client, actor, "demo_b")
    assert first.status_code == 201
    assert create(client, actor, "demo_b").status_code == 200
    before = db.collection("connections").count()
    assert create(client, actor, "demo_c", "second").status_code == 429
    assert db.collection("connections").count() == before
