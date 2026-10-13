from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest

from backend.core.repository import Repository

pytestmark = pytest.mark.integration


def create(client, candidate, token="referral-create", **changes):
    return client.post(
        "/api/v1/referral-requests",
        headers={
            **candidate,
            "Idempotency-Key": token,
        },
        json={
            "referrer_id": "demo_c",
            "job_id": "demo_backend",
            "message": "Please refer me",
            **changes,
        },
    )


def test_referral_complete_workflow_owner_and_history_notifications(
    client, reachable, register, db
):
    candidate, user, referrer = reachable
    outsider, _ = register()
    before = db.collection("notifications").count()
    created = create(client, candidate)
    assert created.status_code == 201, created.text
    doc = created.json()
    route = "/api/v1/referral-requests/" + doc["id"]
    assert doc["candidate_id"] == user["id"] and "idempotency_key" not in doc
    assert client.get(route, headers=outsider).status_code == 404
    assert (
        client.post(
            route + "/accept",
            headers={
                **candidate,
                "If-Match": created.headers["ETag"],
            },
            json={},
        ).status_code
        == 403
    )
    accepted = client.post(
        route + "/accept",
        headers={
            **referrer,
            "If-Match": created.headers["ETag"],
        },
        json={"reason": "Happy to help"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["accepted_at"] and accepted.json()["status"] == "accepted"
    assert (
        client.post(
            route + "/submit",
            headers={
                **referrer,
                "If-Match": created.headers["ETag"],
            },
            json={"evidence_ref": "ats:ticket-123"},
        ).status_code
        == 412
    )
    assert (
        client.post(
            route + "/submit",
            headers={
                **referrer,
                "If-Match": accepted.headers["ETag"],
            },
            json={},
        ).status_code
        == 422
    )
    submitted = client.post(
        route + "/submit",
        headers={
            **referrer,
            "If-Match": accepted.headers["ETag"],
        },
        json={"evidence_ref": "ats:ticket-123"},
    )
    assert submitted.status_code == 200, submitted.text
    completed = client.post(
        route + "/complete",
        headers={
            **referrer,
            "If-Match": submitted.headers["ETag"],
        },
        json={"outcome": "Interview scheduled"},
    )
    assert completed.status_code == 200, completed.text
    assert [h["status"] for h in completed.json()["history"]] == [
        "pending",
        "accepted",
        "submitted",
        "completed",
    ]
    assert completed.json()["history"][-1]["reason"] == "Interview scheduled"
    assert db.collection("notifications").count() == before + 4
    assert (
        client.post(
            route + "/complete",
            headers={
                **referrer,
                "If-Match": completed.headers["ETag"],
            },
            json={"outcome": "Again"},
        ).status_code
        == 409
    )


def test_referral_replay_conflict_unique_triple_and_inboxes(client, reachable, db):
    candidate, _, referrer = reachable
    before = db.collection("notifications").count()
    created, replay = create(client, candidate), create(client, candidate)
    assert created.status_code == 201 and replay.status_code == 200
    assert created.json()["id"] == replay.json()["id"]
    assert db.collection("notifications").count() == before + 1
    assert create(client, candidate, message="Changed").status_code == 409
    assert create(client, candidate, "new-key").status_code == 409
    mine = client.get("/api/v1/referral-requests/me", headers=candidate).json()
    incoming = client.get("/api/v1/referral-requests/incoming", headers=referrer).json()
    assert created.json()["id"] in {r["id"] for r in mine["items"]}
    assert created.json()["id"] in {r["id"] for r in incoming["items"]}


@pytest.mark.parametrize("action,expected", [("reject", "rejected"), ("cancel", "cancelled")])
def test_referral_terminal_transitions_keep_lifetime_unique(client, reachable, action, expected):
    candidate, _, referrer = reachable
    created = create(client, candidate)
    actor = candidate if action == "cancel" else referrer
    route = "/api/v1/referral-requests/" + created.json()["id"]
    result = client.post(
        route + "/" + action,
        headers={
            **actor,
            "If-Match": created.headers["ETag"],
        },
        json={"reason": "Not proceeding"},
    )
    assert result.status_code == 200, result.text
    assert result.json()["status"] == expected
    assert create(client, candidate, "again").status_code == 409


@pytest.mark.parametrize(
    "change,status",
    [
        ({"job_id": "demo_closed"}, 409),
        ({"referrer_id": "demo_f"}, 409),
        ({"referrer_id": "demo_m"}, 409),
        ({"referrer_id": "demo_g"}, 404),
        ({"referrer_id": "missing"}, 404),
    ],
)
def test_create_requires_live_job_employee_and_private_path(client, reachable, db, change, status):
    candidate, _, _ = reachable
    before = db.collection("referral_requests").count()
    result = create(client, candidate, **change)
    assert result.status_code == status, result.text
    assert db.collection("referral_requests").count() == before


@pytest.mark.parametrize("condition", ["privacy", "employment", "connection", "job"])
@pytest.mark.parametrize("stage", ["accept", "submit"])
def test_accept_and_submit_revalidate_graph_policy(client, reachable, db, condition, stage):
    candidate, _, referrer = reachable
    created = create(client, candidate)
    assert created.status_code == 201, created.text
    route = "/api/v1/referral-requests/" + created.json()["id"]
    current = created
    if stage == "submit":
        current = client.post(
            route + "/accept",
            headers={
                **referrer,
                "If-Match": created.headers["ETag"],
            },
            json={},
        )
        assert current.status_code == 200
    if condition == "privacy":
        me = client.get("/api/v1/users/me", headers=referrer)
        hidden = client.patch(
            "/api/v1/users/me/privacy",
            headers={
                **referrer,
                "If-Match": me.headers["ETag"],
            },
            json={**me.json()["privacy"], "allow_in_paths": False},
        )
        assert hidden.status_code == 200
    elif condition == "employment":
        db.aql.execute(
            "FOR e IN works_at FILTER e._from == 'users/demo_c' "
            "AND e._to == 'companies/demo_x' UPDATE e WITH {verified:false} IN works_at"
        )
    elif condition == "connection":
        db.collection("connections").update({"_key": "demo_b_c", "status": "blocked"})
    else:
        db.collection("jobs").update({"_key": "demo_backend", "status": "closed"})
    before = db.collection("notifications").count()
    submitted = client.post(
        route + "/" + stage,
        headers={
            **referrer,
            "If-Match": current.headers["ETag"],
        },
        json={"evidence_ref": "ats:123"} if stage == "submit" else {},
    )
    assert submitted.status_code == 409, submitted.text
    assert db.collection("notifications").count() == before
    assert db.collection("referral_requests").get(created.json()["id"])["status"] == (
        "accepted" if stage == "submit" else "pending"
    )


def test_expiration_is_persisted_by_authorized_batch(client, reachable, login, db):
    candidate, _, referrer = reachable
    admin = login("demo_x", admin=True)
    created = create(client, candidate)
    db.collection("referral_requests").update(
        {"_key": created.json()["id"], "expires_at": "2020-01-01T00:00:00.000Z"}
    )
    current = client.get("/api/v1/referral-requests/" + created.json()["id"], headers=referrer)
    assert (
        client.post(
            "/api/v1/referral-requests/" + created.json()["id"] + "/accept",
            headers={
                **referrer,
                "If-Match": current.headers["ETag"],
            },
            json={},
        ).status_code
        == 409
    )
    assert (
        client.post("/api/v1/admin/referral-requests/expire", headers=candidate).status_code == 403
    )
    expired = client.post("/api/v1/admin/referral-requests/expire", headers=admin)
    assert expired.status_code == 200 and expired.json()["expired"] == 1
    doc = db.collection("referral_requests").get(created.json()["id"])
    assert doc["status"] == "expired" and doc["history"][-1]["status"] == "expired"
    assert (
        client.post("/api/v1/admin/referral-requests/expire", headers=admin).json()["expired"] == 0
    )


def test_concurrent_referral_replay_and_daily_quota(client, reachable, db):
    candidate, _, _ = reachable
    client.app.state.config = replace(client.app.state.config, referral_limit=1)
    before = db.collection("notifications").count()
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: create(client, candidate), range(4)))
    assert sorted(r.status_code for r in results) == [200, 200, 200, 201]
    assert len({r.json()["id"] for r in results}) == 1
    assert db.collection("notifications").count() == before + 1
    assert create(client, candidate, "other-job", job_id="demo_frontend").status_code == 429


def test_concurrent_referrer_per_job_limit(client, reachable, db):
    candidate, _, _ = reachable
    client.app.state.config = replace(client.app.state.config, referrers_per_job=1)
    repo = Repository(db)
    repo.collection = "works_at"
    repo.insert(
        {
            "_from": "users/demo_b",
            "_to": "companies/demo_x",
            "title": "Engineer",
            "department": "Engineering",
            "status": "current",
            "verified": True,
            "start_at": "2020-01-01T00:00:00.000Z",
            "end_at": None,
        }
    )
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda target: create(client, candidate, "referrer-" + target, referrer_id=target),
                ["demo_b", "demo_c"],
            )
        )
    assert sorted(r.status_code for r in results) == [201, 429], [r.text for r in results]


def test_application_attachment_requires_candidate_job_and_consent(client, reachable, db):
    candidate, _, _ = reachable
    invalid = create(client, candidate, application_id="demo_a_backend")
    assert invalid.status_code == 422
    application = client.post(
        "/api/v1/jobs/demo_backend/applications",
        headers=candidate,
        json={"consent": True, "resume_ref": "cv:private"},
    )
    assert application.status_code == 201, application.text
    created = create(client, candidate, application_id=application.json()["id"])
    assert created.status_code == 201, created.text
    assert created.json()["application_id"] == application.json()["id"]
    assert "resume_ref" not in created.json()
