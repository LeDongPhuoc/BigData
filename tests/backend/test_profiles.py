import pytest

pytestmark = pytest.mark.integration


def test_profile_module_validates_salary_modes_and_updates_owner_only(client, login, db):
    actor = login()
    me = client.get("/api/v1/users/me", headers=actor)
    payload = {**me.json()["profile"], "headline": "Python engineer", "experience_years": 8}
    headers = {**actor, "If-Match": me.headers["ETag"]}
    assert (
        client.patch(
            "/api/v1/profiles/me",
            headers=headers,
            json={
                **payload,
                "salary_min": 10,
                "salary_max": 5,
            },
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/v1/profiles/me",
            headers=headers,
            json={
                **payload,
                "work_modes": ["remote", "remote"],
            },
        ).status_code
        == 422
    )
    result = client.patch("/api/v1/profiles/me", headers=headers, json=payload)
    assert result.status_code == 200, result.text
    own = client.get("/api/v1/profiles/me", headers=actor)
    assert own.status_code == 200 and own.json()["profile"]["headline"] == "Python engineer"
    assert db.collection("users").get("demo_a")["profile"]["experience_years"] == 8
    assert client.patch("/api/v1/profiles/demo_b", headers=actor, json=payload).status_code == 404
