"""Summarize recorded audit evidence and verify current local DB/runtime state.

Read-only: never delete resources or export credentials/document bodies.
This report is evidence, not a production readiness certification.
"""

import json
import re
import subprocess
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from arango import ArangoClient

from database.config import Settings
from database.connection import connect
from database.migrate import validate_schema
from database.seed import audit_integrity

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs" / "reports"


def read(name):
    return json.loads((REPORTS / name).read_text(encoding="utf-8"))


def junit(name):
    suites = ET.parse(REPORTS / name).getroot().iter("testsuite")
    result = {key: 0 for key in ("tests", "errors", "failures", "skipped")}
    for suite in suites:
        for key in result:
            result[key] += int(suite.get(key, 0))
    if any(result[key] for key in ("errors", "failures", "skipped")):
        raise RuntimeError("Final test evidence contains failures or skips: " + name)
    return {"report": name, **result}


def image_report(name):
    report = read(name)
    findings = [v for r in report.get("Results", []) for v in r.get("Vulnerabilities", [])]
    high = [v for v in findings if v["Severity"] in ("HIGH", "CRITICAL")]
    return {
        "report": name,
        "recorded_at": report["CreatedAt"],
        "scanned_image_config_digest": report["Metadata"]["ImageID"],
        "package_cve_entries_by_severity": dict(Counter(v["Severity"] for v in findings)),
        "distinct_high_critical_ids": sorted({v["VulnerabilityID"] for v in high}),
        "high_critical_entries_with_fixed_version": sum(bool(v.get("FixedVersion")) for v in high),
        "api_exploitability_proven": False,
    }


def main():
    settings = Settings.load()
    db = connect(settings)
    system = ArangoClient(hosts=settings.url).db(
        "_system", username=settings.username, password=settings.password
    )
    validate_schema(db)
    issues = audit_integrity(db)
    if issues:
        raise RuntimeError("Main database integrity check failed")
    database_pattern = r"jrn_(?:test|e2e|security|bench|restore)_[a-f0-9]{32}"
    owned_databases = sum(bool(re.fullmatch(database_pattern, name)) for name in system.databases())
    owned_users = sum(
        bool(re.fullmatch(r"jrn_(?:e2e|runtime_test)_[a-f0-9]{32}", row["username"]))
        for row in system.users()
    )
    if owned_databases or owned_users:
        raise RuntimeError(
            "Disposable audit databases/users remain; investigate without bulk deletion"
        )
    container_ids = subprocess.check_output(
        ["docker", "compose", "--profile", "web", "ps", "-q"], text=True, cwd=ROOT
    ).split()
    containers = json.loads(
        subprocess.check_output(["docker", "inspect", *container_ids], text=True)
    )
    runtime = {
        c["Config"]["Labels"]["com.docker.compose.service"]: {
            "healthy": c["State"].get("Health", {}).get("Status") == "healthy",
            "image_reference": c["Config"]["Image"],
            "runtime_image_digest": c["Image"],
            "restart_count": c["RestartCount"],
            "oom_killed": c["State"]["OOMKilled"],
        }
        for c in containers
    }
    if set(runtime) != {"backend", "frontend", "arangodb"} or not all(
        r["healthy"] and not r["oom_killed"] for r in runtime.values()
    ):
        raise RuntimeError("Expected local services are not healthy")
    python_dependencies = read("security-python-dependencies-after.json")
    browser = read("frontend-summary.json")
    bandit = read("security-bandit-final.json")
    images = {
        service: image_report(name)
        for service, name in (
            ("backend", "security-backend-image.json"),
            ("frontend", "security-frontend-image-after.json"),
            ("arangodb", "security-arango-image.json"),
        )
    }
    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "production_ready": False,
        "integration": junit("security-verified-integration.xml"),
        "filesystem_security": junit("security-backup-paths.xml"),
        "browser": browser,
        "dependency_advisories": {
            "python_locked_requirements": sum(
                len(d["vulns"]) for d in python_dependencies["dependencies"]
            ),
            "npm_all_dependencies": read("security-npm-dependencies.json")["metadata"][
                "vulnerabilities"
            ],
        },
        "bandit_review": {
            "report": "security-bandit-final.json",
            "raw_severity_counts": {
                k: v for k, v in bandit["metrics"]["_totals"].items() if k.startswith("SEVERITY.")
            },
            "manual_review": "See security-review-2026-10-11.md; raw findings retained",
        },
        "image_scanner": {
            "tool": "Trivy 0.75.0",
            "scanner_image": (
                "aquasec/trivy@sha256:"
                "af6acf9a6b85dfe389a1941505c0ce9efef52a4719635e1a962f022a3d855daa"
            ),
            "scope": "Saved runtime images; no Docker socket; vulnerability DB snapshot",
            "images": images,
        },
        "database": {
            "version": db.version(),
            "schema_indexes_graph": "pass",
            "integrity_issues": [],
            "user_count": db.collection("users").count(),
            "main_migration": read("security-main-migration.json"),
            "query_index_limits": read("security-database.json"),
            "graph_benchmark_report": "security-graph-benchmark.json",
            "disposable_audit_databases_remaining": owned_databases,
            "disposable_audit_users_remaining": owned_users,
        },
        "runtime": runtime,
        "docker_hardening": read("security-docker.json"),
        "proxy_header_check": read("security-proxy.json"),
        "backend_tcp_check": read("backend-http.json"),
        "compiled_frontend_check": read("frontend-deployment.json"),
        "backup_restore": read("recovery.json"),
        "source_secret_scan_report": "security-source.json",
        "open_release_conditions": [
            "HIGH backend/ArangoDB image findings; patch/reachability assessment incomplete",
            "TLS/public ingress and production HTTP/graph/jobs/concurrency workload unverified",
            "ArangoDB OS UID 0; persistent volume ownership rehearsal needed before changing UID",
            "Production PII retention/purge, encrypted backups and periodic restore unverified",
            "Email verification/password reset and signed object downloads not implemented",
        ],
    }
    (REPORTS / "security-summary.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print(
        "Audit summary written; real DB integrity/cleanup/runtime healthy; production_ready=false"
    )


if __name__ == "__main__":
    main()
