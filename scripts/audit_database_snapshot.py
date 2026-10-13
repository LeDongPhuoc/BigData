"""Read-only aggregate inventory; no credentials or personal documents in reports."""

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from backend.modules.exploration.service import catalog
from database.config import Settings
from database.connection import connect


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Report exists: choose a new snapshot filename")
    db = connect(Settings.load())
    collections = []
    seed_fingerprints = {}
    for collection in sorted(db.collections(), key=lambda item: item["name"]):
        name = collection["name"]
        if name.startswith("_"):
            continue
        docs = list(
            db.aql.execute(
                "FOR d IN @@collection FILTER STARTS_WITH(d._key, 'demo_') "
                "SORT d._key RETURN {key:d._key,revision:d._rev}",
                bind_vars={"@collection": name},
                max_runtime=5,
            )
        )
        collections.append(
            {
                "name": name,
                "type": collection["type"],
                "count": db.collection(name).count(),
                "seed_count": len(docs),
            }
        )
        if docs:
            seed_fingerprints[name] = hashlib.sha256(
                json.dumps(docs, sort_keys=True).encode()
            ).hexdigest()
    data = catalog(db)
    report = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "database": db.name,
        "collections": collections,
        "graphs": [
            {"name": graph["name"], "edges": graph["edge_definitions"]} for graph in db.graphs()
        ],
        "catalog": {
            "total": data["total"],
            "seed": sum(item["origin"] == "seed" for item in data["items"]),
            "public": sum(item["origin"] == "public" for item in data["items"]),
        },
        "seed_fingerprints": seed_fingerprints,
        "sample_field_names": {
            "jobs": list(db.collection("jobs").get("demo_backend") or {}),
            "skills": list(db.collection("skills").get("demo_python") or {}),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as target:
        json.dump(report, target, ensure_ascii=False, indent=2)
        target.write("\n")
    print(json.dumps({"collections": len(collections), "catalog": report["catalog"]}))


if __name__ == "__main__":
    main()
