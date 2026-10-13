import pytest

pytestmark = pytest.mark.integration


def test_company_requires_admin_verification_then_owner_can_add_recruiter(
    client, login, register, db
):
    owner, user = register()
    admin = login("demo_x", admin=True)
    created = client.post(
        "/api/v1/companies", headers=owner, json={"name": "Real Company", "slug": "real-company"}
    )
    assert created.status_code == 201, created.text
    company_id = created.json()["id"]
    assert "members" not in created.json()
    route = "/api/v1/companies/" + company_id
    assert client.get(route + "/members", headers=owner).json()[0]["verified"] is False
    assert client.get(route + "/members", headers=admin).json()[0]["user_id"] == user["id"]
    assert (
        client.patch(
            route,
            headers={**owner, "If-Match": created.headers["ETag"]},
            json={"name": "No verification"},
        ).status_code
        == 403
    )
    verify = f"/api/v1/admin/companies/{company_id}/members/{user['id']}/verification"
    assert (
        client.patch(
            verify, headers={**owner, "If-Match": created.headers["ETag"]}, json={"verified": True}
        ).status_code
        == 403
    )
    verified = client.patch(
        verify, headers={**admin, "If-Match": created.headers["ETag"]}, json={"verified": True}
    )
    assert verified.status_code == 200, verified.text
    assert "recruiter" in db.collection("users").get(user["id"])["roles"]
    updated = client.patch(
        route,
        headers={**owner, "If-Match": verified.headers["ETag"]},
        json={"name": "Verified Company"},
    )
    assert updated.status_code == 200
    recruiter, target = register()
    added = client.post(
        route + "/members",
        headers={**owner, "If-Match": updated.headers["ETag"]},
        json={"user_id": target["id"], "role": "recruiter"},
    )
    assert added.status_code == 200, added.text
    assert client.get(route + "/members", headers=recruiter).status_code == 200
    assert (
        client.post(
            route + "/members",
            headers={**recruiter, "If-Match": added.headers["ETag"]},
            json={"user_id": "demo_b", "role": "recruiter"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            route + "/members",
            headers={**owner, "If-Match": added.headers["ETag"]},
            json={"user_id": target["id"], "role": "recruiter"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            route + "/members",
            headers={**owner, "If-Match": added.headers["ETag"]},
            json={"user_id": "demo_b", "role": "owner"},
        ).status_code
        == 403
    )


def test_employment_does_not_grant_company_management(client, login, db):
    actor = login("demo_r")
    # demo_r is a verified employee of Y with no company membership.
    company = client.get("/api/v1/companies/demo_y", headers=actor)
    assert (
        client.patch(
            "/api/v1/companies/demo_y",
            headers={
                **actor,
                "If-Match": company.headers["ETag"],
            },
            json={"name": "Forbidden"},
        ).status_code
        == 403
    )
    assert client.get("/api/v1/companies/demo_y/members", headers=actor).status_code == 403
    assert db.collection("companies").get("demo_y")["name"] != "Forbidden"


def test_employment_admin_updates_verified_edge_atomically(client, login):
    recruiter = login("demo_c")
    company = client.get("/api/v1/companies/demo_x", headers=recruiter)
    route = "/api/v1/companies/demo_x/employees/demo_b"
    payload = {
        "title": "Engineer",
        "department": "Engineering",
        "status": "current",
        "start_at": "2020-01-01T00:00:00.000Z",
        "end_at": None,
    }
    response = client.put(
        route, headers={**recruiter, "If-Match": company.headers["ETag"]}, json=payload
    )
    assert response.status_code == 200, response.text
    employees = client.get("/api/v1/companies/demo_x/employees", headers=recruiter).json()["items"]
    assert "demo_b" in {e["id"] for e in employees}
    invalid = client.put(
        route,
        headers={**recruiter, "If-Match": response.headers["ETag"]},
        json={**payload, "end_at": "2010-01-01T00:00:00.000Z"},
    )
    assert invalid.status_code == 422
