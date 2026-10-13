import pytest

pytestmark = pytest.mark.integration


def test_skill_taxonomy_requires_admin_deduplicates_and_can_archive(client, login, db):
    actor = login()
    admin = login("demo_x", admin=True)
    payload = {"name": "FastAPI", "normalized_name": "fastapi", "category": "backend"}
    assert client.post("/api/v1/skills", headers=actor, json=payload).status_code == 403
    created = client.post("/api/v1/skills", headers=admin, json=payload)
    assert created.status_code == 201, created.text
    assert client.post("/api/v1/skills", headers=admin, json=payload).status_code == 409
    archived = client.patch(
        "/api/v1/skills/" + created.json()["id"],
        headers={
            **admin,
            "If-Match": created.headers["ETag"],
        },
        json={"name": "FastAPI", "category": "backend", "status": "archived"},
    )
    assert archived.status_code == 200, archived.text
    assert (
        client.put(
            "/api/v1/users/me/skills/" + created.json()["id"],
            headers=actor,
            json={"proficiency": 5, "years_experience": 2},
        ).status_code
        == 404
    )
    assert db.collection("skills").get(created.json()["id"])["status"] == "archived"
