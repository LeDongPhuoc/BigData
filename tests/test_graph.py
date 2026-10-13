import pytest

from database.queries import GraphQueries

pytestmark = pytest.mark.integration
ACTOR = "users/demo_a"
COMPANY = "companies/demo_x"
AS_OF = "2026-10-11T00:00:00.000Z"


def paths(db, **options):
    return GraphQueries(db).referral_paths(ACTOR, COMPANY, as_of=AS_OF, **options)


def vertices(row):
    return [vertex["id"] for vertex in row["vertices"]]


def test_core_a_b_c_and_alternative(db):
    rows = paths(db, job_id="jobs/demo_backend")
    assert [vertices(row) for row in rows] == [
        [ACTOR, "users/demo_b", "users/demo_c"],
        [ACTOR, "users/demo_d", "users/demo_e", "users/demo_c"],
    ]
    assert [row["hops"] for row in rows] == [2, 3]
    assert rows[0]["trust"] == pytest.approx(0.85)
    assert rows[0]["current_verified_employee"] is True
    assert rows[0]["next_step"]["referrer_id"] == "users/demo_c"
    assert rows[0]["next_step"]["via_user_id"] == "users/demo_b"


def test_reverse_any_and_shortest(db):
    query = GraphQueries(db)
    assert "users/demo_b" in [row["id"] for row in query.direct_connections("users/demo_c")]
    shortest = query.shortest_path("users/demo_c", ACTOR, as_of=AS_OF)
    assert vertices(shortest) == ["users/demo_c", "users/demo_b", ACTOR]
    assert shortest["hops"] == 2


@pytest.mark.parametrize("status", ["pending", "rejected", "blocked"])
def test_invalid_edge_uses_longer_valid_path(db, status):
    db.collection("connections").update({"_key": "demo_b_c", "status": status})
    rows = paths(db)
    assert len(rows) == 1 and rows[0]["hops"] == 3
    assert GraphQueries(db).shortest_path(ACTOR, "users/demo_c", as_of=AS_OF)["hops"] == 3


@pytest.mark.parametrize("mode", ["soft_delete", "hard_delete"])
def test_broken_edge_and_no_path(db, mode):
    collection = db.collection("connections")
    if mode == "soft_delete":
        collection.update({"_key": "demo_b_c", "deleted_at": AS_OF})
    else:
        db.graph("jobReferralGraph").edge_collection("connections").delete("demo_b_c")
    assert len(paths(db)) == 1
    collection.update({"_key": "demo_e_c", "deleted_at": AS_OF})
    assert paths(db) == []


def test_depth_limit_and_cycles(db):
    assert paths(db, max_depth=1) == []
    assert [row["hops"] for row in paths(db, max_depth=2)] == [2]
    for row in paths(db):
        assert len(vertices(row)) == len(set(vertices(row)))


@pytest.mark.parametrize("field", ["discoverable", "allow_in_paths"])
def test_hidden_intermediate_prunes_branch(db, field):
    user = db.collection("users").get("demo_b")
    user["privacy"][field] = False
    db.collection("users").replace(user)
    assert [row["hops"] for row in paths(db)] == [3]


def test_hidden_employment(db):
    user = db.collection("users").get("demo_c")
    user["privacy"]["employment_visible"] = False
    db.collection("users").replace(user)
    assert paths(db) == []


@pytest.mark.parametrize("status", ["suspended", "deleted"])
def test_inactive_intermediate(db, status):
    db.collection("users").update({"_key": "demo_b", "status": status})
    assert [row["hops"] for row in paths(db)] == [3]


def test_soft_deleted_user(db):
    db.collection("users").update({"_key": "demo_b", "deleted_at": AS_OF})
    assert [row["hops"] for row in paths(db)] == [3]


@pytest.mark.parametrize("change", ["ended", "unverified", "end_boundary", "future_start"])
def test_employment_validity(db, change):
    changes = {
        "ended": {"status": "ended", "end_at": AS_OF},
        "unverified": {"verified": False},
        "end_boundary": {"end_at": AS_OF},
        "future_start": {"start_at": "2099-01-01T00:00:00.000Z"},
    }
    db.collection("works_at").update({"_key": "demo_c", **changes[change]})
    assert paths(db) == []


def test_global_viewer_block_removes_indirect_vertex(db):
    # K is connected to B, but A blocked K. No alternate route may disclose K.
    assert "users/demo_k" not in [row["referrer"]["id"] for row in paths(db)]
    for row in paths(db):
        assert "users/demo_k" not in vertices(row)
    assert GraphQueries(db).shortest_path(ACTOR, "users/demo_k", as_of=AS_OF) is None


def test_employee_filters_and_direct_statuses(db):
    query = GraphQueries(db)
    employees = {row["id"] for row in query.employees(ACTOR, COMPANY, as_of=AS_OF)}
    assert "users/demo_c" in employees and "users/demo_l" in employees
    assert not employees.intersection({f"users/demo_{key}" for key in "fhjk mop".replace(" ", "")})
    direct = {row["id"] for row in query.direct_connections(ACTOR)}
    assert "users/demo_b" in direct
    assert not direct.intersection({f"users/demo_{key}" for key in "gijks"})
    assert "users/demo_c" not in direct  # no direct connection to company X's valid referrer


def test_closed_job_and_wrong_company(db):
    assert paths(db, job_id="jobs/demo_closed") == []
    assert paths(db, job_id="jobs/demo_remote") == []
    db.collection("companies").update({"_key": "demo_x", "status": "archived"})
    assert paths(db) == []


def test_missing_and_inactive_actor(db):
    query = GraphQueries(db)
    assert query.referral_paths("users/absent", COMPANY, as_of=AS_OF) == []
    assert query.referral_paths(ACTOR, "companies/absent", as_of=AS_OF) == []
    assert query.shortest_path(ACTOR, "users/absent", as_of=AS_OF) is None
    db.collection("users").update({"_key": "demo_a", "status": "suspended"})
    assert paths(db) == []
    assert query.job_matches(ACTOR) == []


def test_payload_minimization_and_deterministic_pagination(db):
    rows = paths(db)
    assert paths(db, limit=1)[0] == rows[0]
    assert paths(db, offset=1, limit=1)[0] == rows[1]
    for row in rows:
        for vertex in row["vertices"]:
            assert set(vertex) == {"id", "display_name", "headline"}
        assert all(edge["status"] == "accepted" for edge in row["edges"])


@pytest.mark.parametrize(
    "option",
    [
        {"max_depth": 4},
        {"max_depth": 0},
        {"limit": 101},
        {"offset": -1},
        {"offset": 1001},
        {"limit": True},
        {"target_id": "users/x' RETURN 1"},
    ],
)
def test_invalid_query_parameters(db, option):
    with pytest.raises(ValueError):
        paths(db, **option)


def test_neutral_trust_does_not_invent_probability(db):
    db.collection("connections").update({"_key": "demo_a_b", "trust": None})
    db.collection("connections").update({"_key": "demo_b_c", "trust": None})
    shortest_row = next(row for row in paths(db) if row["hops"] == 2)
    assert shortest_row["trust"] == 0.5


def test_recommended_path_can_differ_from_shortest(db):
    db.collection("connections").update({"_key": "demo_a_b", "trust": 0})
    db.collection("connections").update({"_key": "demo_b_c", "trust": 0})
    assert paths(db)[0]["hops"] == 3
    shortest = GraphQueries(db).shortest_path(ACTOR, "users/demo_c", as_of=AS_OF)
    assert shortest["hops"] == 2
    assert paths(db)[0]["path_score"] > shortest["path_score"]


def test_unconfirmed_acceptance_timestamp_prunes(db):
    db.collection("connections").update({"_key": "demo_b_c", "accepted_at": None})
    assert [row["hops"] for row in paths(db)] == [3]
