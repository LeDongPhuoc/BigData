import pytest

pytestmark = pytest.mark.integration


def test_application_workflow_consent_cv_access_withdrawal(client, register, login, db):
    candidate, user = register()
    recruiter = login("demo_c")
    employee = login("demo_r")
    created = client.post(
        "/api/v1/jobs/demo_backend/applications",
        headers=candidate,
        json={"consent": True, "resume_ref": "cv:private-123"},
    )
    assert created.status_code == 201, created.text
    route = "/api/v1/applications/" + created.json()["id"]
    assert created.json()["candidate_id"] == user["id"]
    assert client.get(route, headers=employee).status_code == 404
    assert client.get(route, headers=recruiter).json()["resume_ref"] == "cv:private-123"
    assert client.get("/api/v1/jobs/demo_backend/applications", headers=employee).status_code == 403
    assert (
        client.post(
            "/api/v1/jobs/demo_backend/applications", headers=candidate, json={"consent": True}
        ).status_code
        == 409
    )
    assert (
        client.patch(
            route + "/status",
            headers={**candidate, "If-Match": created.headers["ETag"]},
            json={"status": "reviewing"},
        ).status_code
        == 404
    )
    assert (
        client.patch(
            route + "/status",
            headers={**recruiter, "If-Match": created.headers["ETag"]},
            json={"status": "offered"},
        ).status_code
        == 409
    )
    reviewed = client.patch(
        route + "/status",
        headers={
            **recruiter,
            "If-Match": created.headers["ETag"],
        },
        json={"status": "reviewing"},
    )
    assert reviewed.status_code == 200, reviewed.text
    withdrawn = client.post(
        route + "/withdraw",
        headers={
            **candidate,
            "If-Match": reviewed.headers["ETag"],
        },
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["consent"] is False and withdrawn.json()["resume_ref"] is None
    assert client.get(route, headers=recruiter).status_code == 404
    assert db.collection("applications").get(created.json()["id"])["status"] == "withdrawn"


def test_closed_job_and_missing_consent_cannot_create_application(client, register):
    candidate, _ = register()
    assert (
        client.post(
            "/api/v1/jobs/demo_closed/applications", headers=candidate, json={"consent": True}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/jobs/demo_backend/applications", headers=candidate, json={"consent": False}
        ).status_code
        == 422
    )
