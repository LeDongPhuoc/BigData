import pytest

from database.public_catalog import import_catalog, load_catalog

pytestmark = pytest.mark.integration


def test_matching_and_opportunities_use_real_skills_and_live_paths(client, login):
    actor = login()
    result = client.get("/api/v1/jobs/demo_backend/matching", headers=actor)
    assert result.status_code == 200, result.text
    match = result.json()["items"][0]
    assert match["eligible"] and match["score"] > 0
    assert match["explanation"]["components"] and match["explanation"]["missing_required"] == []
    opportunity = client.get("/api/v1/graph/jobs/demo_backend/opportunities", headers=actor)
    assert opportunity.status_code == 200, opportunity.text
    assert opportunity.json()["items"][0]["best_path"]["referrer"]["id"] == "demo_c"
    assert client.delete("/api/v1/users/me/skills/demo_python", headers=actor).status_code == 204
    changed = client.get("/api/v1/jobs/demo_backend/matching", headers=actor).json()["items"][0]
    assert not changed["eligible"]
    assert changed["explanation"]["missing_required"] == ["demo_python"]
    assert (
        client.get("/api/v1/graph/jobs/demo_backend/opportunities", headers=actor).json()["items"]
        == []
    )


def test_matching_role_and_list_bounds(client, login):
    admin = login("demo_x", admin=True)
    assert client.get("/api/v1/matching/jobs", headers=admin).status_code == 403
    actor = login()
    response = client.get("/api/v1/matching/jobs?limit=1", headers=actor)
    assert response.status_code == 200, response.text
    assert len(response.json()["items"]) == 1 and response.json()["has_more"]


def test_recommendations_follow_saved_java_postgresql_aws_and_paginate(client, db, register):
    headers, _ = register()
    import_catalog(db, load_catalog(), retire_test_listings=True)
    route = "/api/v1/matching/jobs"
    assert client.get(route, headers=headers, params={"matched_only": True}).json()["items"] == []
    skills = {skill["name"]: skill["_key"] for skill in db.collection("skills").all()}
    for name in ("Java", "PostgreSQL", "AWS"):
        response = client.put(
            "/api/v1/users/me/skills/" + skills[name],
            headers=headers,
            json={"proficiency": 4, "years_experience": 3},
        )
        assert response.status_code == 200, response.text
    response = client.get(route, headers=headers, params={"matched_only": True, "limit": 100})
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert len(rows) > 1
    assert [row["score"] for row in rows] == sorted((row["score"] for row in rows), reverse=True)
    assert {
        skill["name"]
        for row in rows
        for skill in row["explanation"]["requirements"]
        if skill["matched"]
    } == {"Java", "PostgreSQL", "AWS"}
    assert all(any(s["matched"] for s in row["explanation"]["requirements"]) for row in rows)
    assert all(row["job"]["source"] and row["job"]["location"] for row in rows)
    first = client.get(route, headers=headers, params={"matched_only": True, "limit": 1}).json()
    second = client.get(
        route, headers=headers, params={"matched_only": True, "limit": 1, "offset": 1}
    ).json()
    assert first["has_more"] and first["items"] == rows[:1] and second["items"] == rows[1:2]
    for name in ("Java", "PostgreSQL", "AWS"):
        assert (
            client.delete("/api/v1/users/me/skills/" + skills[name], headers=headers).status_code
            == 204
        )
    assert client.get(route, headers=headers, params={"matched_only": True}).json()["items"] == []


def test_recommendation_filters_skill_search_and_actor_isolation(client, db, register, login):
    headers, _ = register()
    import_catalog(db, load_catalog(), retire_test_listings=True)
    aws = next(s for s in db.collection("skills").all() if s["name"] == "AWS")
    assert (
        client.put(
            "/api/v1/users/me/skills/" + aws["_key"],
            headers=headers,
            json={"proficiency": 4, "years_experience": 3},
        ).status_code
        == 200
    )
    route = "/api/v1/matching/jobs"
    params = {"matched_only": True, "q": " AWS ", "company_id": "public_grab", "limit": 100}
    response = client.get(route, headers=headers, params=params)
    assert response.status_code == 200, response.text
    rows = response.json()["items"]
    assert rows and all(row["job"]["company_id"] == "public_grab" for row in rows)
    for change in (
        {"q": "' OR true RETURN job //"},
        {"location": "nonexistent-city"},
        {"company_id": "public_bosch_group"},
    ):
        assert client.get(route, headers=headers, params={**params, **change}).json()["items"] == []
    selected = rows[0]["job"]
    filtered = client.get(
        route,
        headers=headers,
        params={
            **params,
            "location": selected["location"],
            "level": selected["level"],
            "work_mode": selected["work_mode"],
        },
    ).json()["items"]
    assert filtered and all(row["job"]["location"] == selected["location"] for row in filtered)
    other, _ = register()
    assert (
        client.get(route, headers=other, params={**params, "actor_id": "demo_a"}).json()["items"]
        == []
    )
    assert client.get(route).status_code == 401
    assert client.get(route, headers=login("demo_e", admin=True)).status_code == 403
    for change in ({"matched_only": "invalid"}, {"q": "x" * 161}, {"level": "invalid"}):
        assert client.get(route, headers=headers, params={**params, **change}).status_code == 422
