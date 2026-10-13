"""Small, repeatable synthetic benchmark. Always uses a disposable, owned database."""

import json
import math
import statistics
import time
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from arango import ArangoClient

from database.connection import connect
from database.migrate import migrate
from database.queries import GraphQueries
from database.seed import SEED_TIME, connection_document, demo_documents, seed

AS_OF = "2026-10-11T00:00:00.000Z"


def _extend_network(db, branching=10):
    template = demo_documents()["users"][0]
    employment = demo_documents()["works_at"][0]
    users, edges, works = [], [], []
    frontier = ["users/demo_a"]
    count = 0
    for depth in range(1, 4):
        next_frontier = []
        for parent in frontier:
            for _ in range(branching):
                count += 1
                key = f"bench_{count}"
                user = deepcopy(template)
                user.update(
                    _key=key, email=f"bench-{count}@example.test", display_name=f"Synthetic {count}"
                )
                users.append(user)
                user_id = f"users/{key}"
                edges.append(connection_document(parent, user_id, key=key, trust=0.8))
                if depth == 3:
                    work = deepcopy(employment)
                    work.update(_key=key, _from=user_id)
                    works.append(work)
                next_frontier.append(user_id)
        frontier = next_frontier
    tx = db.begin_transaction(write=["users", "connections", "works_at"], allow_implicit=False)
    try:
        for name, docs in (("users", users), ("connections", edges), ("works_at", works)):
            results = tx.collection(name).insert_many(docs)
            for result in results:
                if isinstance(result, Exception):
                    raise result
        tx.commit_transaction()
    except Exception:
        tx.abort_transaction()
        raise
    return frontier[-1]


def benchmark(settings, iterations=20, output=Path("docs/reports/benchmark.json")):
    name = "jrn_bench_" + uuid4().hex
    system = ArangoClient(hosts=settings.url).db(
        "_system", username=settings.username, password=settings.password
    )
    db = connect(replace(settings, database=name), create=True)
    try:
        migrate(db)
        seed(db)
        target = _extend_network(db)
        repository = GraphQueries(db)
        actor = "users/demo_a"
        cases = {
            "direct": ("direct_connections", repository.parameters(actor)),
            "employees": (
                "company_employees",
                repository.parameters(actor, company_id="companies/demo_x", as_of=AS_OF),
            ),
            **{
                f"paths_depth_{depth}": (
                    "referral_paths",
                    repository.parameters(
                        actor, company_id="companies/demo_x", max_depth=depth, as_of=AS_OF
                    ),
                )
                for depth in (1, 2, 3)
            },
            "shortest_valid": (
                "referral_paths",
                repository.parameters(actor, target_id=target, limit=1, as_of=AS_OF),
            ),
            "job_matches": ("job_matches", repository.parameters(actor)),
            "jobs_with_referral": (
                "jobs_with_referral",
                {
                    **repository.parameters(actor, limit=1, as_of=AS_OF),
                    "job_offset": 0,
                    "job_limit": 20,
                },
            ),
        }
        cases["shortest_valid"][1]["shortest_only"] = True
        results = {}
        for label, (query, params) in cases.items():
            repository.execute(query, params)  # warmup, cache remains disabled
            elapsed = []
            total_start = time.perf_counter()
            for _ in range(iterations):
                start = time.perf_counter()
                rows = repository.execute(query, params)
                elapsed.append((time.perf_counter() - start) * 1000)
            total = time.perf_counter() - total_start
            profiled = repository.execute(query, params, profile=True)
            results[label] = {
                "iterations": iterations,
                "p50_ms": statistics.median(elapsed),
                "p95_ms": sorted(elapsed)[math.ceil(0.95 * len(elapsed)) - 1],
                "serial_requests_per_second": iterations / total,
                "result_count": len(rows),
                "errors": 0,
                "explain": repository.explain(query, params),
                "statistics": profiled["statistics"],
                "profile": profiled["profile"],
            }
        report = {
            "recorded_for_client_date": "2026-10-11",
            "server_version": db.version(),
            "seed_time": SEED_TIME,
            "as_of": AS_OF,
            "synthetic": True,
            "network": {"branching": 10, "depth": 3, "additional_reachable_users": 1110},
            "dataset_counts": {
                c["name"]: db.collection(c["name"]).count()
                for c in db.collections()
                if not c["system"]
            },
            "limits": "Local Docker single server; serial warm queries; not a production load test",
            "queries": results,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "report": str(output),
            "server_version": report["server_version"],
            "dataset_counts": report["dataset_counts"],
            "latency_ms": {
                k: {"p50": round(v["p50_ms"], 2), "p95": round(v["p95_ms"], 2)}
                for k, v in results.items()
            },
        }
    finally:
        # `name` is freshly generated by this function, never supplied by the caller.
        if not name.startswith("jrn_bench_") or len(name) != len("jrn_bench_") + 32:
            raise RuntimeError("Refusing to delete an unowned benchmark database")
        system.delete_database(name)
