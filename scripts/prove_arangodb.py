"""Print reproducible ArangoDB evidence using an owned, temporary real database."""

import json
import sys
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from arango import ArangoClient
from arango.exceptions import ArangoServerError

from database.config import Settings
from database.connection import connect
from database.migrate import migrate, utc_now
from database.queries import GraphQueries
from database.seed import seed


def summarize(rows):
    return [
        {
            "vertices": [vertex["id"] for vertex in row["vertices"]],
            "hops": row["hops"],
            "path_score": row["path_score"],
            "current_verified_employee": row["current_verified_employee"],
        }
        for row in rows
    ]


def prove(settings):
    name = "jrn_proof_" + uuid4().hex
    client = ArangoClient(hosts=settings.url)
    system = client.db("_system", username=settings.username, password=settings.password)
    result = {
        "checked_at": utc_now(),
        "database": name,
        "version": system.version(),
        "data_kind": "isolated_test_fixture",
        "main_database_modified": False,
    }
    created = False
    try:
        db = connect(replace(settings, database=name), create=True)
        created = True
        migrate(db)
        seed(db)
        query = GraphQueries(db)
        params = query.parameters(
            "users/demo_a",
            company_id="companies/demo_x",
            job_id="jobs/demo_backend",
            as_of="2026-10-11T00:00:00.000Z",
        )

        def paths():
            return query.execute("referral_paths", params)

        baseline = paths()
        assert [row["hops"] for row in baseline] == [2, 3]
        result["baseline_paths"] = summarize(baseline)
        plan = query.explain("referral_paths", params)
        result["plan_node_types"] = sorted({node["type"] for node in plan["nodes"]})
        result["plan_index_names"] = sorted(
            {
                index["name"]
                for node in plan["nodes"]
                if node["type"] == "IndexNode"
                for index in node["indexes"]
            }
        )
        assert "TraversalNode" in result["plan_node_types"]
        assert "company_current_employees" in result["plan_index_names"]
        statistics = query.execute("referral_paths", params, profile=True)["statistics"]
        result["profile_statistics"] = {
            key: statistics[key]
            for key in ("execution_time", "scanned_full", "scanned_index", "peak_memory_usage")
        }

        db.collection("connections").update({"_key": "demo_b_c", "status": "blocked"})
        rows = paths()
        assert [row["hops"] for row in rows] == [3]
        result["after_block_b_c"] = summarize(rows)
        db.collection("connections").update({"_key": "demo_b_c", "status": "accepted"})

        user = db.collection("users").get("demo_b")
        original = user["privacy"]["allow_in_paths"]
        user["privacy"]["allow_in_paths"] = False
        db.collection("users").replace(user)
        rows = paths()
        assert [row["hops"] for row in rows] == [3]
        result["after_b_disallows_paths"] = summarize(rows)
        user = db.collection("users").get("demo_b")
        user["privacy"]["allow_in_paths"] = original
        db.collection("users").replace(user)

        db.collection("works_at").update({"_key": "demo_c", "verified": False})
        rows = paths()
        assert rows == []
        result["after_c_employment_unverified"] = summarize(rows)

        notice = dict(db.collection("notifications").get("demo_a"))
        notice.pop("_id")
        notice.pop("_rev")
        notice.update(_key="proof_atomic", event_key="proof_atomic")
        tx = db.begin_transaction(write=["notifications", "audit_logs"], allow_implicit=False)
        try:
            tx.collection("notifications").insert(notice)
            tx.collection("audit_logs").insert({"_key": "proof_bad_audit", "invalid": True})
            raise AssertionError("Invalid audit document was accepted")
        except ArangoServerError as error:
            assert error.error_code == 1620
            result["transaction_schema_error_code"] = error.error_code
        finally:
            tx.abort_transaction()
        result["transaction_rolled_back"] = not db.collection("notifications").has(
            "proof_atomic"
        ) and not db.collection("audit_logs").has("proof_bad_audit")
        assert result["transaction_rolled_back"]
    finally:
        try:
            if created:
                assert name.startswith("jrn_proof_")
                assert len(name) == len("jrn_proof_") + 32
                assert name != settings.database
                system.delete_database(name)
            result["isolated_database_cleaned_up"] = not system.has_database(name)
        finally:
            client.close()
    assert result["isolated_database_cleaned_up"]
    return result


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    result = prove(Settings.load())
    report = Path(__file__).resolve().parents[1] / "docs/reports/arango-behavior-proof.json"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
