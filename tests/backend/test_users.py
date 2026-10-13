import pytest

pytestmark = pytest.mark.integration


def test_profile_privacy_revision_and_owner_authorization(client, login, db):
    a, c = login(), login("demo_c")
    current = client.get("/api/v1/users/me", headers=c)
    patched = client.patch(
        "/api/v1/users/me",
        headers={**c, "If-Match": current.headers["ETag"]},
        json={"display_name": "Updated Referrer"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.headers["ETag"] != current.headers["ETag"]
    stale = client.patch(
        "/api/v1/users/me",
        headers={**c, "If-Match": current.headers["ETag"]},
        json={"display_name": "Stale"},
    )
    assert stale.status_code == 412
    assert (
        client.patch(
            "/api/v1/users/me", headers=c, json={"display_name": "No revision"}
        ).status_code
        == 428
    )
    assert (
        client.patch(
            "/api/v1/users/me",
            headers={**c, "If-Match": patched.headers["ETag"]},
            json={"roles": ["admin"]},
        ).status_code
        == 422
    )
    profile = client.get("/api/v1/users/demo_c/profile", headers=a)
    assert profile.status_code == 200 and "email" not in profile.json()
    assert profile.json()["employment"]
    privacy = client.patch(
        "/api/v1/users/me/privacy",
        headers={
            **c,
            "If-Match": patched.headers["ETag"],
        },
        json={
            "discoverable": True,
            "allow_in_paths": False,
            "employment_visible": False,
            "skills_visible": False,
        },
    )
    assert privacy.status_code == 200, privacy.text
    public = client.get("/api/v1/users/demo_c/profile", headers=a).json()
    assert public["employment"] is None and public["skills"] is None
    assert (
        client.get("/api/v1/graph/referral-paths?company_id=demo_x", headers=a).json()["items"]
        == []
    )
    hidden = client.patch(
        "/api/v1/users/me/privacy",
        headers={
            **c,
            "If-Match": privacy.headers["ETag"],
        },
        json={**privacy.json()["privacy"], "discoverable": False},
    )
    assert hidden.status_code == 200
    assert client.get("/api/v1/users/demo_c/profile", headers=a).status_code == 404
    assert db.collection("users").get("demo_c")["display_name"] == "Updated Referrer"


def test_self_skills_validation_and_cannot_claim_verified(client, login, db):
    headers = login()
    payload = {"proficiency": 5, "years_experience": 5}
    assert (
        client.put(
            "/api/v1/users/me/skills/demo_python",
            headers=headers,
            json={**payload, "verified": True},
        ).status_code
        == 422
    )
    response = client.put("/api/v1/users/me/skills/demo_python", headers=headers, json=payload)
    assert response.status_code == 200, response.text
    assert response.json()["verified"] is False
    assert (
        client.put("/api/v1/users/me/skills/missing", headers=headers, json=payload).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/users/me/skills/demo_python",
            headers=headers,
            json={**payload, "proficiency": 6},
        ).status_code
        == 422
    )
    assert client.delete("/api/v1/users/me/skills/demo_python", headers=headers).status_code == 204
    assert not list(
        db.aql.execute(
            "FOR s IN has_skill FILTER s._from == 'users/demo_a' "
            "AND s._to == 'skills/demo_python' RETURN 1"
        )
    )


def test_blocked_user_profile_unavailable(client, login):
    headers = login()
    assert client.get("/api/v1/users/demo_k/profile", headers=headers).status_code == 404
    assert client.get("/api/v1/users/demo_j/profile", headers=headers).status_code == 404
    assert client.get("/api/v1/users/demo_g/profile", headers=headers).status_code == 404
    assert client.get("/api/v1/users/users%2Fdemo_c/profile", headers=headers).status_code != 200
