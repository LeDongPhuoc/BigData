import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy

import pytest
from arango.exceptions import ArangoServerError

from database.migrate import MIGRATIONS, SchemaDriftError, manifests, migrate, validate_schema
from database.queries import GraphQueries
from database.relationships import insert_relationship
from database.seed import audit_integrity, demo_documents, insert_connection, seed

pytestmark = pytest.mark.integration
VERSIONS = [data["version"] for data, _ in manifests()]


def test_bootstrap_and_seed_repeat_without_overwriting(db):
    before = {name: db.collection(name).count() for name in demo_documents()}
    db.collection("users").update({"_key": "demo_a", "display_name": "User-edited name"})
    assert migrate(db) == VERSIONS
    assert seed(db) == before
    assert db.collection("users").get("demo_a")["display_name"] == "User-edited name"
    assert db.collection("users").count() == 24
    assert {r["status"] for r in db.collection("referral_requests").all()} == {
        "pending",
        "accepted",
        "rejected",
        "cancelled",
        "expired",
        "submitted",
        "completed",
    }
    assert [r["status"] for r in db.collection("schema_migrations").all()] == ["applied"] * len(
        VERSIONS
    )
    assert audit_integrity(db) == []


def test_incompatible_collection_type_preserves_data(empty_db):
    collection = empty_db.create_collection("connections")
    collection.insert({"_key": "sentinel", "unchanged": True})
    with pytest.raises(SchemaDriftError, match="collection type"):
        migrate(empty_db)
    assert collection.get("sentinel")["unchanged"] is True
    assert empty_db.collection("schema_migrations").get("1")["status"] == "failed"


def test_partial_migration_resumes(empty_db):
    spec = manifests()[0][0]["collections"]["users"]
    empty_db.create_collection("users", schema=spec["schema"])
    assert migrate(empty_db) == VERSIONS
    validate_schema(empty_db)


def test_schema_drift_fails_instead_of_silently_repairing(db):
    schema = deepcopy(manifests()[0][0]["collections"]["users"]["schema"])
    schema["level"] = "none"
    db.collection("users").configure(schema=schema)
    with pytest.raises(SchemaDriftError, match="Schema drift"):
        migrate(db)
    assert db.collection("users").properties()["schema"]["level"] == "none"


def test_named_graph_drift_fails(db):
    db.graph("jobReferralGraph").delete_edge_definition("has_skill", purge=False)
    with pytest.raises(SchemaDriftError, match="graph definitions"):
        migrate(db)


def test_index_drift_fails(db):
    index = next(i for i in db.collection("users").indexes() if i["name"] == "user_email_unique")
    db.collection("users").delete_index(index["id"])
    with pytest.raises(SchemaDriftError, match="index"):
        migrate(db)


def test_checksum_change_fails(db, tmp_path):
    for file in MIGRATIONS.glob("*.json"):
        (tmp_path / file.name).write_bytes(file.read_bytes())
    path = tmp_path / "001_initial_schema.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["description"] = "Changed applied migration"
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(SchemaDriftError, match="checksum"):
        migrate(db, tmp_path)


def test_lock_prevents_concurrent_migration(db):
    db.collection("migration_locks").insert({"_key": "schema", "owner": "other-process"})
    with pytest.raises(RuntimeError, match="lock exists"):
        migrate(db)
    assert db.collection("migration_locks").get("schema")["owner"] == "other-process"


@pytest.mark.parametrize(
    "collection",
    [
        "users",
        "applications",
        "referral_requests",
        "job_at_company",
        "has_skill",
        "job_requires_skill",
        "works_at",
    ],
)
def test_business_unique_indexes(db, collection):
    doc = deepcopy(demo_documents()[collection][0])
    doc["_key"] = "duplicate"
    with pytest.raises(ArangoServerError) as failure:
        db.collection(collection).insert(doc)
    assert failure.value.error_code == 1210


def test_reverse_duplicate_protected_even_for_direct_collection_write(db):
    doc = deepcopy(demo_documents()["connections"][0])
    doc.update(_key="reverse_duplicate", _from=doc["_to"], _to=doc["_from"], pair_key="spoofed")
    with pytest.raises(ArangoServerError) as failure:
        db.collection("connections").insert(doc)
    assert failure.value.error_code == 1210  # computed pair_key is canonical and unique


def test_canonical_writer_race(db):
    def attempt(reverse):
        try:
            pair = ["users/demo_t", "users/demo_u"]
            if reverse:
                pair.reverse()
            insert_connection(db, *pair, key="race_reverse" if reverse else "race_forward")
            return "inserted"
        except ArangoServerError as error:
            assert error.error_code in (1200, 1210)
            return "conflict" if error.error_code == 1200 else "duplicate"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, [False, True]))
    assert outcomes.count("inserted") == 1
    assert len([outcome for outcome in outcomes if outcome in ("duplicate", "conflict")]) == 1
    assert db.collection("connections").find({"pair_key": "users/demo_t|users/demo_u"}).count() == 1
    assert audit_integrity(db) == []


@pytest.mark.parametrize(
    "left,right", [("users/demo_a", "users/demo_a"), ("companies/demo_x", "users/demo_a")]
)
def test_connection_writer_rejects_invalid_pairs(db, left, right):
    with pytest.raises(ValueError):
        insert_connection(db, left, right)


def test_writer_rejects_dangling_and_wrong_collection_endpoints(db):
    source = demo_documents()["works_at"][0]
    for target in ("companies/absent", "users/demo_a"):
        with pytest.raises(ValueError):
            insert_relationship(db, "works_at", {**source, "_key": "bad_endpoint", "_to": target})
    assert not db.collection("works_at").has("bad_endpoint")


@pytest.mark.parametrize(
    "collection,field,value",
    [
        ("users", "status", "invalid"),
        ("connections", "trust", 1.1),
        ("has_skill", "proficiency", 6),
        ("has_skill", "proficiency", 1.5),
        ("works_at", "verified", "yes"),
        ("referral_requests", "status", "invented"),
        ("job_requires_skill", "importance", -1),
    ],
)
def test_strict_schema_rejects_invalid_data(db, collection, field, value):
    original = demo_documents()[collection][0]
    with pytest.raises(ArangoServerError) as failure:
        db.collection(collection).update({"_key": original["_key"], field: value})
    assert failure.value.error_code == 1620


def test_multi_collection_abort_is_atomic(db):
    tx = db.begin_transaction(write=["notifications", "audit_logs"], allow_implicit=False)
    notice = {
        **demo_documents()["notifications"][0],
        "_key": "atomic_notice",
        "event_key": "atomic",
    }
    try:
        tx.collection("notifications").insert(notice)
        with pytest.raises(ArangoServerError):
            tx.collection("audit_logs").insert({"_key": "atomic_audit", "invalid": True})
    finally:
        tx.abort_transaction()
    assert not db.collection("notifications").has("atomic_notice")
    assert not db.collection("audit_logs").has("atomic_audit")


def test_integrity_audit_detects_raw_dangling_edge(db):
    doc = {**demo_documents()["works_at"][0], "_key": "raw_dangling", "_from": "users/absent"}
    db.collection("works_at").insert(doc)
    assert any("Invalid endpoint" in issue for issue in audit_integrity(db))


def test_seed_rolls_back_on_existing_integrity_violation(db):
    doc = {**demo_documents()["works_at"][0], "_key": "raw_dangling", "_from": "users/absent"}
    db.collection("works_at").insert(doc)
    db.collection("notifications").delete("demo_a")
    with pytest.raises(ValueError, match="integrity failed"):
        seed(db)
    assert not db.collection("notifications").has("demo_a")


def test_explain_profile_and_indexes(db):
    query = GraphQueries(db)
    params = query.parameters(
        "users/demo_a", company_id="companies/demo_x", as_of="2026-10-11T00:00:00.000Z"
    )
    plan = query.explain("referral_paths", params)
    nodes = plan["nodes"]
    assert any(node["type"] == "TraversalNode" for node in nodes)
    index_nodes = [node for node in nodes if node["type"] == "IndexNode"]
    assert any(
        index["name"] == "company_current_employees"
        for node in index_nodes
        for index in node["indexes"]
    )
    profiled = query.execute("referral_paths", params, profile=True)
    assert len(profiled["rows"]) == 2
    assert profiled["statistics"]["execution_time"] >= 0
    assert profiled["profile"]


def _schema_update_manifest(tmp_path, required=False):
    for file in MIGRATIONS.glob("*.json"):
        (tmp_path / file.name).write_bytes(file.read_bytes())
    before = deepcopy(manifests()[0][0]["collections"]["users"]["schema"])
    after = deepcopy(before)
    after["rule"]["properties"]["timezone"] = {"type": "string"}
    if required:
        after["rule"]["required"].append("timezone")
    change = {
        "version": len(VERSIONS) + 1,
        "description": "Optional timezone field",
        "schema_updates": {"users": {"before": before, "after": after}},
        "recovery": "Resume or forward repair, no destructive rollback",
    }
    (tmp_path / f"{len(VERSIONS) + 1:03d}_timezone.json").write_text(
        json.dumps(change),
        encoding="utf-8",
    )
    return after


def test_append_schema_migration_and_repeat(db, tmp_path):
    _schema_update_manifest(tmp_path)
    assert migrate(db, tmp_path) == [*VERSIONS, len(VERSIONS) + 1]
    db.collection("users").update({"_key": "demo_a", "timezone": "Asia/Saigon"})
    assert migrate(db, tmp_path) == [*VERSIONS, len(VERSIONS) + 1]
    validate_schema(db, tmp_path)
    assert db.collection("users").get("demo_a")["timezone"] == "Asia/Saigon"


def test_schema_migration_rejects_incompatible_existing_data(db, tmp_path):
    _schema_update_manifest(tmp_path, required=True)
    with pytest.raises(SchemaDriftError, match="Existing data violates"):
        migrate(db, tmp_path)
    assert db.collection("schema_migrations").get(str(len(VERSIONS) + 1))["status"] == "failed"
    # A failed forward migration keeps the data intact but quarantines startup until
    # the operator resumes/repairs its journal, even if collection DDL was not changed.
    with pytest.raises(SchemaDriftError, match="Migration history"):
        validate_schema(db)
    assert "timezone" not in db.collection("users").properties()["schema"]["rule"]["properties"]
    assert db.collection("users").count() == 24
