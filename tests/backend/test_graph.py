import pytest

pytestmark = pytest.mark.integration


def test_graph_http_returns_safe_ranked_paths_and_pagination(client, login):
    actor = login()
    result = client.get("/api/v1/graph/referral-paths?company_id=demo_x&limit=1", headers=actor)
    assert result.status_code == 200, result.text
    page = result.json()
    assert page["has_more"] and len(page["items"]) == 1
    path = page["items"][0]
    assert path["hops"] == 2 and path["referrer"]["id"] == "demo_c"
    assert all("email" not in v and "privacy" not in v for v in path["vertices"])
    second = client.get(
        "/api/v1/graph/referral-paths?company_id=demo_x&offset=1&limit=1", headers=actor
    )
    assert second.json()["items"][0]["hops"] == 3 and not second.json()["has_more"]
    assert (
        client.get(
            "/api/v1/graph/referral-paths?company_id=demo_x&max_depth=4", headers=actor
        ).status_code
        == 422
    )
    assert client.get("/api/v1/graph/referral-paths?company_id=demo_x").status_code == 401
    assert (
        client.get("/api/v1/graph/referral-paths?company_id=missing", headers=actor).json()["items"]
        == []
    )
    employees = client.get("/api/v1/companies/demo_x/employees", headers=actor)
    assert employees.status_code == 200
    assert "demo_h" not in {u["id"] for u in employees.json()["items"]}


def test_block_of_intermediate_filters_alternate_paths(client, login):
    actor = login()
    edge = client.get("/api/v1/connections/demo_a_b", headers=actor)
    assert edge.status_code == 200
    assert (
        client.post(
            "/api/v1/connections/demo_a_b/block",
            headers={
                **actor,
                "If-Match": edge.headers["ETag"],
            },
        ).status_code
        == 200
    )
    paths = client.get("/api/v1/graph/referral-paths?company_id=demo_x", headers=actor).json()[
        "items"
    ]
    assert len(paths) == 1 and all(v["id"] != "demo_b" for v in paths[0]["vertices"])
