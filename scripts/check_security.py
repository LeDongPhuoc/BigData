"""Repeatable security evidence, using owned databases and a real Docker deployment.

Reports contain hashes and metadata only. Never persist environment values, tokens,
passwords, document bodies or raw docker inspect/config output.
"""

import hashlib
import http.client
import json
import re
import subprocess
import tempfile
import time
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from arango import ArangoClient
from arango.exceptions import ArangoServerError

from database.config import Settings
from database.connection import connect
from database.migrate import MIGRATIONS, migrate
from database.seed import audit_integrity, demo_documents

if __package__:
    from .check_backup_restore import copy_dump
else:
    from check_backup_restore import copy_dump

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "docs" / "reports"


def write(name, data):
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def source_review():
    credentials = []
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in line:
            name, value = line.split("=", 1)
            if ("PASSWORD" in name or "SECRET" in name) and len(value.strip()) >= 16:
                credentials.append(value.strip())
    files = []
    for directory in (
        "backend",
        "database",
        "scripts",
        "frontend/src",
        "frontend/e2e",
        "frontend/dist",
        "tests",
        "docs",
    ):
        files.extend(
            p
            for p in (ROOT / directory).rglob("*")
            if p.is_file()
            and p != REPORTS / "security-source.json"
            and p.suffix
            in {".py", ".json", ".aql", ".ts", ".tsx", ".js", ".md", ".html", ".xml", ".css"}
            and "__pycache__" not in p.parts
        )
    files.extend(
        ROOT / p
        for p in (
            "Dockerfile",
            "compose.yaml",
            "pyproject.toml",
            "requirements.lock",
            "frontend/Dockerfile",
            "frontend/nginx.conf",
            "frontend/package.json",
            "frontend/package-lock.json",
        )
    )
    signatures = re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|"
        r"\bAKIA[0-9A-Z]{16}\b|\bghp_[A-Za-z0-9]{36}\b|\bsk_live_[A-Za-z0-9]{20,}\b"
    )
    leaked, inventory = [], []
    for path in sorted(set(files)):
        raw = path.read_bytes()
        content = raw.decode("utf-8", errors="replace")
        relative = path.relative_to(ROOT).as_posix()
        # This checker defines provider patterns; these literals are not credentials.
        signature_match = relative != "scripts/check_security.py" and signatures.search(content)
        if any(value in content for value in credentials) or signature_match:
            leaked.append(relative)
        inventory.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    write(
        "security-source.json",
        {
            "scanned_files": len(inventory),
            "known_local_secret_matches": leaked,
            "scope": (
                "working tree, reports and compiled assets; excludes local env/backups/tool venvs"
            ),
            "git_history_available": (ROOT / ".git").exists(),
            "inventory": inventory,
        },
    )
    if leaked:
        raise RuntimeError("Sensitive value matched in file(s); inspect redacted report paths")


def database_review(settings):
    name = "jrn_security_" + uuid4().hex
    system = ArangoClient(hosts=settings.url).db(
        "_system", username=settings.username, password=settings.password
    )
    db = connect(replace(settings, database=name), create=True)
    try:
        with tempfile.TemporaryDirectory(prefix="jrn-schema-") as directory:
            previous = Path(directory)
            for path in MIGRATIONS.glob("00[1-3]_*.json"):
                (previous / path.name).write_bytes(path.read_bytes())
            migrate(db, previous)
        # Trusted synthetic fixture writer: seed() checks the latest schema, so the
        # pre-004 comparison writes the unchanged demo documents directly in one tx.
        data = demo_documents()
        tx = db.begin_transaction(write=list(data), allow_implicit=False)
        try:
            for collection, docs in data.items():
                for doc in docs:
                    tx.collection(collection).insert(doc)
            tx.commit_transaction()
        except BaseException:
            tx.abort_transaction()
            raise
        queries = {
            collection: "FOR d IN " + collection + " FILTER d.status == 'active' "
            "SORT d.created_at DESC,d._key ASC LIMIT 0,21 RETURN d"
            for collection in ("companies", "skills")
        }

        def plans():
            return {
                collection: [
                    {"type": n["type"], "indexes": [i["name"] for i in n.get("indexes", [])]}
                    for n in db.aql.explain(query)["nodes"]
                    if n["type"] in ("EnumerateCollectionNode", "IndexNode", "SortNode")
                ]
                for collection, query in queries.items()
            }

        before = plans()
        counts = {c: db.collection(c).count() for c in data}
        versions = migrate(db)
        after = plans()
        if counts != {c: db.collection(c).count() for c in data} or audit_integrity(db):
            raise RuntimeError("Migration changed business counts or integrity")
        if any(not any(n["type"] == "IndexNode" for n in nodes) for nodes in after.values()):
            raise RuntimeError("Expected listing index was not selected")
        aborts = {}
        for label, source, options in (
            (
                "runtime",
                "FOR n IN 1..1000000 LET wait = SLEEP(0.01) RETURN {n,wait}",
                {"max_runtime": 0.05, "memory_limit": 1048576},
            ),
            (
                "memory",
                "RETURN (FOR n IN 1..1000000 SORT RAND() RETURN {n,text:REPEAT('x',100)})",
                {"max_runtime": 2, "memory_limit": 1048576},
            ),
        ):
            started = time.perf_counter()
            try:
                list(db.aql.execute(source, cache=False, **options))
            except ArangoServerError as error:
                expected_code = 1500 if label == "runtime" else 32
                if error.error_code != expected_code:
                    raise RuntimeError(
                        "Unexpected query error; resource limit not proven"
                    ) from error
                aborts[label] = {
                    "error_code": error.error_code,
                    "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
                    "limits": options,
                }
            else:
                raise RuntimeError("Expected query resource-limit rejection did not occur")
        write(
            "security-database.json",
            {
                "database": db.version(),
                "migration_versions": versions,
                "before_indexes": before,
                "after_indexes": after,
                "business_counts_unchanged": True,
                "integrity_issues": [],
                "query_aborts": aborts,
            },
        )
    finally:
        if not re.fullmatch(r"jrn_security_[a-f0-9]{32}", name):
            raise RuntimeError("Refusing to clean a database not owned by this check")
        system.delete_database(name)


def deployment_review():
    container_ids = subprocess.check_output(
        ["docker", "compose", "--profile", "web", "ps", "-q"], text=True
    ).split()
    containers = json.loads(
        subprocess.check_output(["docker", "inspect", *container_ids], text=True)
    )
    details = {}
    for container in containers:
        service = container["Config"]["Labels"]["com.docker.compose.service"]
        config = container["HostConfig"]
        details[service] = {
            "healthy": container["State"].get("Health", {}).get("Status") == "healthy",
            "user": container["Config"]["User"],
            "read_only": config["ReadonlyRootfs"],
            "cap_drop": config["CapDrop"],
            "security_opt": config["SecurityOpt"],
            "pids_limit": config["PidsLimit"],
            "memory_limit": config["Memory"],
            "loopback_only": all(
                b["HostIp"] == "127.0.0.1"
                for values in (config["PortBindings"] or {}).values()
                for b in values or []
            ),
        }
        if not all(
            (
                details[service]["healthy"],
                details[service]["read_only"],
                "ALL" in config["CapDrop"],
                details[service]["loopback_only"],
                config["PidsLimit"] > 0,
                config["Memory"] > 0,
                any(s.startswith("no-new-privileges") for s in config["SecurityOpt"]),
            )
        ):
            raise RuntimeError("Container hardening/health check failed: " + service)
    http_results = {}
    for port in (8000, 5173):
        for chunked in (False, True):
            connection = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
            payload = b'{"password":"' + b"x" * 131073 + b'"}'
            connection.request(
                "POST",
                "/api/v1/auth/login",
                body=iter([payload[:65536], payload[65536:]]) if chunked else payload,
                headers={"Content-Type": "application/json"},
                encode_chunked=chunked,
            )
            response = connection.getresponse()
            response.read()
            http_results[f"{port}_chunked_{chunked}"] = response.status
            connection.close()
            if response.status != 413:
                raise RuntimeError("Deployed HTTP body limit not enforced")
    write(
        "security-docker.json",
        {
            "containers": details,
            "oversized_http": http_results,
            "database_os_user_is_root": details["arangodb"]["user"] in ("", "0"),
        },
    )


def upgrade_local_main(report_name="security-main-migration.json"):
    """Operator action: call only with API writers stopped for this local workspace."""
    settings = Settings.load()
    if (settings.url, settings.username, settings.database) != (
        "http://127.0.0.1:8529",
        "root",
        "job_referral",
    ):
        raise ValueError("Main upgrade check is restricted to this local Compose database")
    db = connect(settings)

    def snapshot():
        return {
            c["name"]: hashlib.sha256(
                json.dumps(
                    sorted(db.collection(c["name"]).all(), key=lambda d: d["_key"]),
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode()
            ).hexdigest()
            for c in db.collections()
            if not c["system"] and c["name"] not in ("schema_migrations", "migration_locks")
        }

    before = snapshot()
    token = uuid4().hex
    dump = "/tmp/jrn-security-migration-" + token
    backup = ROOT / "backups" / ("security-migration-" + token)
    backup.parent.mkdir(exist_ok=True)
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "arangodb",
            "sh",
            "-c",
            "umask 077; exec arangodump --server.username root "
            '--server.password "$ARANGO_ROOT_PASSWORD" '
            '--server.database "$1" --include-system-collections true --output-directory "$2"',
            "sh",
            settings.database,
            dump,
        ],
        check=True,
        capture_output=True,
    )
    container = subprocess.check_output(
        ["docker", "compose", "ps", "-q", "arangodb"], text=True
    ).strip()
    copy_dump(container, dump, backup)
    versions = migrate(db)
    if snapshot() != before:
        raise RuntimeError("Business document hashes changed across the migration")
    write(
        report_name,
        {
            "migration_versions": versions,
            "all_business_document_hashes_unchanged": True,
            "backup": backup.relative_to(ROOT).as_posix(),
            "business_collection_hashes": before,
            "user_count": db.collection("users").count(),
        },
    )
    if not re.fullmatch(r"/tmp/jrn-security-migration-[a-f0-9]{32}", dump):
        raise RuntimeError("Refusing to remove an unowned container dump directory")
    subprocess.run(
        ["docker", "compose", "exec", "-T", "arangodb", "rm", "-rf", "--", dump],
        check=True,
        capture_output=True,
    )
    print("Main migration applied; backup kept locally; all business document hashes unchanged")


def main():
    settings = Settings.load()
    source_review()
    database_review(settings)
    deployment_review()
    print(
        "Security evidence: source scan, migration/indexes, resource aborts and Docker/HTTP passed"
    )


if __name__ == "__main__":
    main()
