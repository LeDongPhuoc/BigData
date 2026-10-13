"""Public catalog acceptance against actual ArangoDB and authorized HTTP actors."""

import hashlib
import json
from copy import deepcopy

import pytest

from database.migrate import MIGRATIONS, migrate, validate_schema
from database.public_catalog import import_catalog, load_catalog
from database.seed import audit_integrity, demo_documents

pytestmark = pytest.mark.integration


def hashes(db, names=None):
    names = names or [c["name"] for c in db.collections() if not c["system"]]
    return {
        name: hashlib.sha256(
            json.dumps(
                sorted(db.collection(name).all(), key=lambda d: d["_key"]), sort_keys=True
            ).encode()
        ).hexdigest()
        for name in names
    }


def test_optional_provenance_migration_preserves_existing_data(empty_db, tmp_path):
    for path in MIGRATIONS.glob("00[1-4]_*.json"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    migrate(empty_db, tmp_path)
    for name, documents in demo_documents().items():
        for document in documents:
            empty_db.collection(name).insert(document)
    before = hashes(empty_db, list(demo_documents()))
    assert migrate(empty_db) == [1, 2, 3, 4, 5]
    validate_schema(empty_db)
    assert hashes(empty_db, list(demo_documents())) == before
    assert audit_integrity(empty_db) == []


def test_public_import_is_idempotent_and_preserves_personal_auth_and_history(db, register):
    _, user = register()
    protected = [
        "auth_credentials",
        "auth_sessions",
        "auth_families",
        "applications",
        "referral_requests",
        "notifications",
        "audit_logs",
        "connections",
        "works_at",
    ]
    before = hashes(db, protected)
    personal = db.collection("users").get(user["id"])
    catalog = load_catalog()
    imported = import_catalog(db, catalog, retire_test_listings=True)
    assert imported["integrity"] == "pass"
    assert hashes(db, protected) == before
    assert db.collection("users").get(user["id"]) == personal
    assert db.collection("users").count() == 25
    assert all(
        db.collection("jobs").get(j["_key"])["status"] == "archived"
        for j in demo_documents()["jobs"]
    )
    assert all(db.collection("companies").get(c.id)["members"] == [] for c in catalog.companies)
    assert all("demo" not in u["display_name"].lower() for u in db.collection("users").all())
    after = hashes(db)
    repeated = import_catalog(db, catalog, retire_test_listings=True)
    assert repeated["created"] == repeated["updated"] == {}
    assert hashes(db) == after
    assert audit_integrity(db) == []


def test_import_conflict_rolls_back_every_collection(db):
    catalog = load_catalog()
    third = catalog.companies[-1]
    existing = deepcopy(demo_documents()["companies"][0])
    existing.update(_key=third.id, slug="operator-owned-company", name="Operator-owned company")
    db.collection("companies").insert(existing)
    before = hashes(db)
    with pytest.raises(ValueError, match="managed company membership"):
        import_catalog(db, catalog)
    assert hashes(db) == before


def test_import_rejects_edge_identity_collision_without_partial_writes(db):
    catalog = load_catalog()
    existing = db.collection("job_at_company").get("demo_frontend")
    replacement = {k: v for k, v in existing.items() if k not in ("_id", "_rev")}
    replacement["_key"] = catalog.jobs[0].id + "_company"
    db.collection("job_at_company").delete(existing)
    db.collection("job_at_company").insert(replacement)
    assert audit_integrity(db) == []
    before = hashes(db)
    with pytest.raises(ValueError, match="edge endpoints"):
        import_catalog(db, catalog)
    assert hashes(db) == before


@pytest.mark.parametrize(
    "mutation", ["missing_company", "source_host", "source_identity", "duplicate_job"]
)
def test_invalid_catalog_is_rejected_before_database_mutation(db, mutation):
    catalog = load_catalog()
    jobs = list(catalog.jobs)
    if mutation == "missing_company":
        jobs[0] = jobs[0].model_copy(update={"company_id": "public_missing"})
    elif mutation == "source_host":
        jobs[0] = jobs[0].model_copy(
            update={
                "source": jobs[0].source.model_copy(update={"url": "https://127.0.0.1/private"}),
            }
        )
    elif mutation == "source_identity":
        jobs[0] = jobs[0].model_copy(
            update={
                "source": jobs[0].source.model_copy(update={"external_id": "different"}),
            }
        )
    else:
        jobs.append(jobs[0])
    before = hashes(db)
    with pytest.raises(ValueError):
        import_catalog(db, catalog.model_copy(update={"jobs": jobs}))
    assert hashes(db) == before


def test_public_api_exposes_sources_unknown_fields_and_enforces_ownership(db, client, register):
    headers, _ = register()
    catalog = load_catalog()
    import_catalog(db, catalog, retire_test_listings=True)
    listing = client.get("/api/v1/jobs?limit=100", headers=headers)
    assert listing.status_code == 200
    assert len(listing.json()["items"]) == len(catalog.jobs)
    assert all(
        item["source"]["url"].startswith("https://jobs.smartrecruiters.com/")
        for item in listing.json()["items"]
    )
    job = next(j for j in catalog.jobs if j.min_experience_years is None)
    detail = client.get("/api/v1/jobs/" + job.id, headers=headers)
    assert detail.status_code == 200
    assert detail.json()["min_experience_years"] is None
    assert detail.json()["salary_min"] is detail.json()["salary_max"] is None
    matching = client.get("/api/v1/jobs/" + job.id + "/matching", headers=headers)
    assert matching.status_code == 200
    assert matching.json()["items"][0]["explanation"]["components"]["experience"] == 0
    company = client.get("/api/v1/companies/" + job.company_id, headers=headers)
    assert company.status_code == 200 and "members" not in company.json()
    assert company.json()["source"]["publisher"] == job.source.publisher
    assert (
        client.patch(
            "/api/v1/companies/" + job.company_id, headers=headers, json={"name": "Stolen employer"}
        ).status_code
        == 403
    )
    assert (
        client.get("/api/v1/companies/" + job.company_id + "/members", headers=headers).status_code
        == 403
    )
    paths = client.get(
        "/api/v1/graph/referral-paths",
        headers=headers,
        params={"company_id": job.company_id, "job_id": job.id},
    )
    assert paths.status_code == 200 and paths.json()["items"] == []


def test_clients_cannot_forge_public_provenance(client, register):
    headers, _ = register()
    source = load_catalog().companies[0].source.model_dump()
    response = client.post(
        "/api/v1/companies",
        headers=headers,
        json={"name": "Fake source", "slug": "fake-source", "source": source},
    )
    assert response.status_code == 422


def test_authorized_job_edit_clears_external_attribution(db, client, login):
    catalog = load_catalog()
    import_catalog(db, catalog)
    headers = login("demo_l")
    job = catalog.jobs[0]
    # Test-only verified manager, in the disposable fixture database.
    db.collection("companies").update(
        {
            "_key": job.company_id,
            "members": [{"user_id": "users/demo_l", "role": "owner", "verified": True}],
        }
    )
    record = db.collection("jobs").get(job.id)
    payload = job.model_dump(exclude={"id", "company_id", "skill_slugs", "published_at", "source"})
    payload["title"] = "Locally edited position"
    response = client.patch(
        "/api/v1/jobs/" + job.id,
        headers={**headers, "If-Match": f'"{record["_rev"]}"'},
        json=payload,
    )
    assert response.status_code == 200
    assert response.json()["source"] is None
    before = hashes(db)
    with pytest.raises(ValueError):
        import_catalog(db, catalog)
    assert hashes(db) == before
