import argparse
import json
import sys
from pathlib import Path

from database.config import Settings
from database.connection import connect
from database.migrate import migrate, validate_schema
from database.queries import GraphQueries
from database.seed import audit_integrity, seed


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Job Referral ArangoDB foundation")
    parser.add_argument(
        "command",
        choices=["bootstrap", "seed", "verify", "demo", "benchmark", "unlock", "import-public"],
    )
    parser.add_argument(
        "--confirm-stopped",
        action="store_true",
        help="Only unlock after confirming the previous migration process stopped",
    )
    parser.add_argument("--catalog", type=Path, help="Validated public catalog JSON snapshot")
    parser.add_argument("--retire-test-listings", action="store_true")
    args = parser.parse_args()
    settings = Settings.load()
    if args.command == "benchmark":
        from database.benchmark import benchmark

        print(json.dumps(benchmark(settings), ensure_ascii=False, indent=2))
        return
    db = connect(settings, create=args.command == "bootstrap")
    if args.command == "bootstrap":
        result = {"database": settings.database, "version": db.version(), "migrations": migrate(db)}
    elif args.command == "seed":
        result = {"fictional_demo_counts": seed(db)}
    elif args.command == "import-public":
        from database.public_catalog import DEFAULT_CATALOG, import_catalog, load_catalog

        result = import_catalog(
            db,
            load_catalog(args.catalog or DEFAULT_CATALOG),
            retire_test_listings=args.retire_test_listings,
        )
    elif args.command == "verify":
        validate_schema(db)
        issues = audit_integrity(db)
        if issues:
            raise RuntimeError("Integrity audit failed: " + "; ".join(issues))
        result = {"schema": "valid", "integrity": "valid", "version": db.version()}
    elif args.command == "unlock":
        if not args.confirm_stopped:
            parser.error(
                "unlock requires --confirm-stopped after verifying the process is no longer running"
            )
        db.collection("migration_locks").delete("schema", ignore_missing=True)
        result = {"migration_lock": "removed"}
    else:
        query = GraphQueries(db)
        result = {
            "fictional_demo": True,
            "paths": query.referral_paths(
                "users/demo_a", "companies/demo_x", job_id="jobs/demo_backend"
            ),
            "jobs": query.jobs_with_referral("users/demo_a"),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
