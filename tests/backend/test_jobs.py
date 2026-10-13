import pytest

pytestmark = pytest.mark.integration


def payload(**changes):
    return {
        "company_id": "demo_x",
        "title": "API Engineer",
        "description": "Backend role",
        "location": "HCMC",
        "work_mode": "remote",
        "level": "mid",
        "min_experience_years": 1,
        "salary_min": 10000000,
        "salary_max": 30000000,
        "requirements": [{"skill_id": "demo_python", "min_proficiency": 2}],
        **changes,
    }


def test_job_employer_requirements_revision_and_close(client, login, db):
    candidate, recruiter = login(), login("demo_c")
    assert client.post("/api/v1/jobs", headers=candidate, json=payload()).status_code == 403
    created = client.post("/api/v1/jobs", headers=recruiter, json=payload())
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["company_id"] == "demo_x" and data["requirements"][0]["skill_id"] == "demo_python"
    route = "/api/v1/jobs/" + data["id"]
    assert client.get(route, headers=candidate).status_code == 200
    updates = payload(title="Senior Engineer")
    updates.pop("company_id")
    changed = client.patch(
        route, headers={**recruiter, "If-Match": created.headers["ETag"]}, json=updates
    )
    assert changed.status_code == 200, changed.text
    assert (
        client.patch(
            route, headers={**recruiter, "If-Match": created.headers["ETag"]}, json=updates
        ).status_code
        == 412
    )
    assert (
        client.patch(
            route,
            headers={**recruiter, "If-Match": changed.headers["ETag"]},
            json={**updates, "company_id": "demo_y"},
        ).status_code
        == 422
    )
    closed = client.post(
        route + "/close", headers={**recruiter, "If-Match": changed.headers["ETag"]}
    )
    assert closed.status_code == 200 and closed.json()["status"] == "closed"
    assert client.get(route, headers=candidate).status_code == 404
    assert client.get(route, headers=recruiter).status_code == 200
    assert client.get(route + "/matching", headers=candidate).json()["items"] == []
    assert (
        len(
            list(
                db.aql.execute(
                    "FOR e IN job_at_company FILTER e._from == @job RETURN e",
                    bind_vars={"job": "jobs/" + data["id"]},
                )
            )
        )
        == 1
    )


def test_invalid_skills_roll_back_job_edges_and_audit(client, login, db):
    headers = login("demo_c")
    names = ("jobs", "job_at_company", "job_requires_skill", "audit_logs")
    before = {name: db.collection(name).count() for name in names}
    invalid = client.post(
        "/api/v1/jobs", headers=headers, json=payload(requirements=[{"skill_id": "missing"}])
    )
    assert invalid.status_code == 422
    assert {name: db.collection(name).count() for name in names} == before
    assert (
        client.post("/api/v1/jobs", headers=headers, json=payload(salary_min=50000000)).status_code
        == 422
    )
    assert (
        client.post(
            "/api/v1/jobs",
            headers=headers,
            json=payload(
                requirements=[
                    {"skill_id": "demo_python"},
                    {"skill_id": "demo_python"},
                ]
            ),
        ).status_code
        == 422
    )


def test_job_list_pagination_only_active_open_jobs(client, login):
    headers = login()
    result = client.get("/api/v1/jobs?limit=1", headers=headers)
    assert result.status_code == 200
    assert len(result.json()["items"]) == 1 and result.json()["has_more"]
    assert all(j["status"] == "open" for j in result.json()["items"])
    assert client.get("/api/v1/jobs?limit=101", headers=headers).status_code == 422
    assert client.get("/api/v1/jobs?offset=-1", headers=headers).status_code == 422
    scoped = client.get("/api/v1/companies/demo_x/jobs", headers=headers).json()["items"]
    assert scoped and all(j["company_id"] == "demo_x" for j in scoped)


def test_search_filters_precede_pagination_and_use_bound_values(client, login):
    recruiter, candidate = login("demo_c"), login()
    first = client.post(
        "/api/v1/jobs", headers=recruiter, json=payload(title="Searchable Engineer Alpha")
    ).json()
    second = client.post(
        "/api/v1/jobs", headers=recruiter, json=payload(title="Searchable Engineer Beta")
    ).json()
    query = {
        "q": " SEARCHABLE ",
        "location": "hcm",
        "work_mode": "remote",
        "level": "mid",
        "company_id": "demo_x",
        "limit": 1,
    }
    result = client.get("/api/v1/jobs", headers=candidate, params=query)
    assert result.status_code == 200, result.text
    assert result.json()["has_more"] and len(result.json()["items"]) == 1
    next_page = client.get("/api/v1/jobs", headers=candidate, params={**query, "offset": 1})
    found = {result.json()["items"][0]["id"], next_page.json()["items"][0]["id"]}
    assert found == {first["id"], second["id"]} and not next_page.json()["has_more"]
    for changes in (
        {"location": "Hanoi"},
        {"work_mode": "onsite"},
        {"level": "lead"},
        {"company_id": "demo_y"},
        {"q": "' OR true RETURN j //"},
    ):
        response = client.get("/api/v1/jobs", headers=candidate, params={**query, **changes})
        assert response.status_code == 200 and response.json()["items"] == []
    for changes in ({"q": "x" * 161}, {"location": "x" * 121}, {"work_mode": "invalid"}):
        assert (
            client.get("/api/v1/jobs", headers=candidate, params={**query, **changes}).status_code
            == 422
        )


def test_search_uses_skill_edges_when_title_and_description_do_not_mention_skill(client, login):
    recruiter, candidate = login("demo_c"), login()
    created = client.post(
        "/api/v1/jobs",
        headers=recruiter,
        json=payload(
            title="Skill Edge Engineer", description="A role with structured requirements"
        ),
    )
    assert created.status_code == 201, created.text
    response = client.get(
        "/api/v1/jobs",
        headers=candidate,
        params={"q": " PYTHON ", "company_id": "demo_x", "limit": 100},
    )
    assert response.status_code == 200, response.text
    assert created.json()["id"] in {row["id"] for row in response.json()["items"]}
