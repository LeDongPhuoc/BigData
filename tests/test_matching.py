import pytest

from database.queries import GraphQueries

pytestmark = pytest.mark.integration
ACTOR = "users/demo_a"


def test_matching_components_and_network_cannot_override_skills(db):
    query = GraphQueries(db)
    rows = {row["job"]["id"]: row for row in query.job_matches(ACTOR)}
    backend = rows["jobs/demo_backend"]
    assert backend["eligible"] is True
    assert backend["score"] == pytest.approx(0.92)
    assert backend["explanation"]["required_ratio"] == 1
    assert backend["explanation"]["preferred_ratio"] == 0
    assert backend["explanation"]["salary_overlap"] is True
    assert rows["jobs/demo_frontend"]["eligible"] is False
    assert rows["jobs/demo_frontend"]["explanation"]["missing_required"] == ["skills/demo_react"]
    assert "jobs/demo_closed" not in rows
    assert rows["jobs/demo_isolated"]["eligible"] is True
    opportunities = query.jobs_with_referral(ACTOR, as_of="2026-10-11T00:00:00.000Z")
    ids = {row["job"]["id"] for row in opportunities}
    assert "jobs/demo_backend" in ids and "jobs/demo_remote" in ids
    assert "jobs/demo_frontend" not in ids and "jobs/demo_isolated" not in ids
    scores = [row["score"] for row in opportunities]
    assert scores == sorted(scores, reverse=True)


def test_missing_skills_and_proficiency(db):
    query = GraphQueries(db)
    assert (
        query.job_matches("users/demo_q", job_id="jobs/demo_backend")[0]["explanation"][
            "components"
        ]["skill"]
        == 0
    )
    db.collection("has_skill").update({"_key": "demo_a_python", "proficiency": 1})
    row = query.job_matches(ACTOR, job_id="jobs/demo_backend")[0]
    assert row["eligible"] is False
    assert "skills/demo_python" in row["explanation"]["missing_required"]


def test_preferences_salary_and_insufficient_experience(db):
    db.collection("users").update(
        {
            "_key": "demo_a",
            "profile": {
                "experience_years": 1,
                "location": "hanoi",
                "level": "junior",
                "work_modes": ["onsite"],
                "salary_min": None,
                "salary_max": None,
            },
        }
    )
    row = GraphQueries(db).job_matches(ACTOR, job_id="jobs/demo_backend")[0]
    scores = row["explanation"]["components"]
    assert scores["experience"] == pytest.approx(1 / 3)
    assert scores["location"] == scores["level"] == scores["work_mode"] == 0
    assert row["explanation"]["salary_overlap"] is None
    assert row["eligible"] is False


def test_owner_can_match_even_when_skills_hidden(db):
    user = db.collection("users").get("demo_a")
    user["privacy"]["skills_visible"] = False
    db.collection("users").replace(user)
    assert GraphQueries(db).job_matches(ACTOR, job_id="jobs/demo_backend")[0][
        "score"
    ] == pytest.approx(0.92)


def test_no_requirements_and_salary_disjoint(db):
    row = GraphQueries(db).job_matches(ACTOR, job_id="jobs/demo_no_requirements")[0]
    assert row["explanation"]["components"]["skill"] == 0
    db.collection("jobs").update(
        {"_key": "demo_backend", "salary_min": 50000000, "salary_max": 60000000}
    )
    assert (
        GraphQueries(db).job_matches(ACTOR, job_id="jobs/demo_backend")[0]["explanation"][
            "salary_overlap"
        ]
        is False
    )


def test_matching_weights_validation(db):
    with pytest.raises(ValueError):
        GraphQueries(db, weights={"skill": float("nan")})
    custom = {"skill": 1, "experience": 0, "location": 0, "level": 0, "work_mode": 0}
    assert GraphQueries(db, weights=custom).job_matches(ACTOR, job_id="jobs/demo_backend")[0][
        "score"
    ] == pytest.approx(0.8)
