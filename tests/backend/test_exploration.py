"""Exploration stays read-only and distinguishes missing data from matching."""

from backend.modules.exploration.api import PreviewProfile
from backend.modules.exploration.service import location_matches, recommend


def test_catalog_auth_projection_and_preserves_seed(client, db, login):
    assert client.get("/api/v1/exploration/catalog").status_code == 401
    headers = login()
    before = {d["_key"]: d["_rev"] for d in db.collection("jobs").all()}
    result = client.get("/api/v1/exploration/catalog", headers=headers)
    assert result.status_code == 200, result.text
    data = result.json()
    assert data["total"] == 5 and not data["truncated"] and not data["vietjobs_loaded"]
    assert "demo_closed" not in {j["id"] for j in data["items"]}
    assert all(j["origin"] == "seed" for j in data["items"])
    backend = next(j for j in data["items"] if j["id"] == "demo_backend")
    assert {s["name"] for s in backend["requirements"]} == {"python", "sql", "arango"}
    assert not ({"_key", "_id", "_rev"} & set(backend))
    assert before == {d["_key"]: d["_rev"] for d in db.collection("jobs").all()}


def test_similar_excludes_self_closed_and_empty_sets(client, login):
    headers = login()
    result = client.get("/api/v1/exploration/jobs/demo_backend/similar", headers=headers)
    assert result.status_code == 200, result.text
    rows = result.json()["items"]
    assert {r["job"]["id"] for r in rows} == {"demo_isolated", "demo_remote"}
    assert all(abs(r["score"] - 1 / 3) < 1e-8 for r in rows)
    assert (
        client.get("/api/v1/exploration/jobs/demo_no_requirements/similar", headers=headers).json()[
            "items"
        ]
        == []
    )
    assert (
        client.get("/api/v1/exploration/jobs/demo_closed/similar", headers=headers).status_code
        == 404
    )


def test_preview_matching_gap_validation_and_no_profile_write(client, db, login):
    headers = login()
    before = db.collection("users").get("demo_a")
    path = "/api/v1/exploration/recommendations"
    assert client.post(path, headers=headers, json={}).status_code == 422
    assert (
        client.post(path, headers=headers, json={"skill_ids": ["not_a_skill"]}).status_code == 422
    )
    result = client.post(path, headers=headers, json={"skill_ids": ["demo_python"]})
    assert result.status_code == 200, result.text
    rows = result.json()["items"]
    backend = next(r for r in rows if r["job"]["id"] == "demo_backend")
    assert {s["id"] for s in backend["gap"]} == {"demo_sql", "demo_arango"}
    assert backend["coverage"] == 100
    assert db.collection("users").get("demo_a")["_rev"] == before["_rev"]


def test_unknown_requirements_have_no_positive_skill_evidence():
    jobs = [
        {
            "id": "empty",
            "requirements": [],
            "experience": None,
            "location": "hcm",
            "work_mode": "unspecified",
        },
        {
            "id": "known",
            "requirements": [{"id": "python", "name": "Python"}],
            "experience": 2,
            "location": "hcm",
            "work_mode": "hybrid",
        },
    ]
    rows = recommend(jobs, PreviewProfile(skill_ids=["python"], experience=1))
    assert rows[0]["job"]["id"] == "known"
    assert rows[0]["score"] < 100  # One year does not fully meet two years.
    assert rows[1]["observed"] is None and rows[1]["coverage"] == 0 and rows[1]["score"] == 0


def test_location_aliases_tokens_and_policy(client, login):
    assert location_matches("hcm", "hà nội, hồ chí minh")
    assert location_matches("Hanoi", "hà nội")
    assert not location_matches("Nam", "Việt Nam")
    result = client.get("/api/v1/exploration/policy", headers=login())
    assert result.status_code == 200
    assert sum(result.json()["weights"].values()) == 1
    assert result.json()["maximum_limit"] == 50 and not result.json()["calibrated"]
