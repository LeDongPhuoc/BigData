"""Browser acceptance against a real HTTP backend and an owned, disposable ArangoDB.

Creates credentials only in the test database. Secrets are passed in process environment,
never CLI arguments or reports. Both HTTP processes and test DB/user are cleaned in finally.
"""

import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from arango import ArangoClient

from backend.core.provisioning import provision_runtime_user
from backend.core.security import hash_password
from backend.modules.auth.repository import AuthRepository
from database.config import Settings
from database.connection import connect
from database.migrate import migrate, utc_now
from database.public_catalog import Catalog, import_catalog, load_catalog
from database.seed import demo_documents, seed

ROOT = Path(__file__).resolve().parents[1]


def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_http(url, process):
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("Owned HTTP process exited; inspect frontend/test-results logs")
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (OSError, TimeoutError):
            time.sleep(0.25)
    raise RuntimeError("HTTP readiness timed out")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def redact_artifacts(artifacts, report_prefix, owned_secrets):
    files = [*artifacts.rglob("*"), *(ROOT / "docs/reports").glob(f"{report_prefix}-*")]
    for path in files:
        if (
            path.is_symlink()
            or not path.is_file()
            or path.suffix not in {".md", ".log", ".json", ".xml", ".txt"}
        ):
            continue
        content = path.read_text(encoding="utf-8")
        redacted = content
        for secret in owned_secrets:
            if secret:
                redacted = redacted.replace(secret, "[REDACTED_TEST_SECRET]")
        if redacted != content:
            path.write_text(redacted, encoding="utf-8")


def main():
    os.chdir(ROOT)
    report_prefix = os.environ.get("JRN_E2E_REPORT_PREFIX") or "frontend"
    if not re.fullmatch(r"[a-z0-9-]{1,40}", report_prefix):
        raise ValueError("JRN_E2E_REPORT_PREFIX must be a safe report filename prefix")
    settings = Settings.load()
    system = ArangoClient(hosts=settings.url).db(
        "_system", username=settings.username, password=settings.password
    )
    version = system.version()
    assert version.startswith("3.12."), "Real ArangoDB 3.12 is required"
    suffix = uuid4().hex
    name, username = "jrn_e2e_" + suffix, "jrn_e2e_" + suffix
    config = replace(settings, database=name)
    processes = []
    user_created = False
    logs = []
    owned_secrets = []
    artifacts = ROOT / "frontend" / "test-results"
    artifacts.mkdir(parents=True, exist_ok=True)
    db = connect(config, create=True)
    try:
        migrate(db)
        seed(db)
        public_catalog = load_catalog()
        public_job = public_catalog.jobs[0].model_copy(update={"skill_slugs": []})
        recommendation_skills = {"java", "postgresql", "aws", "typescript"}
        recommendation_jobs = [
            next(
                job for job in public_catalog.jobs if {"postgresql", "aws"} <= set(job.skill_slugs)
            ),
            next(
                job
                for job in public_catalog.jobs
                if job.company_id == "public_grab" and "java" in job.skill_slugs
            ),
        ]
        recommendation_jobs = [
            job.model_copy(
                update={
                    "skill_slugs": [
                        slug for slug in job.skill_slugs if slug in recommendation_skills
                    ]
                }
            )
            for job in recommendation_jobs
        ]
        company_ids = {public_job.company_id, *(job.company_id for job in recommendation_jobs)}
        # Actual attributed postings in this owned fixture, preserving legacy
        # graph fixtures and adding no fabricated employer memberships.
        import_catalog(
            db,
            Catalog(
                format_version=1,
                retrieved_at=public_catalog.retrieved_at,
                companies=[c for c in public_catalog.companies if c.id in company_ids],
                skills=[s for s in public_catalog.skills if s.slug in recommendation_skills],
                jobs=[public_job, *recommendation_jobs],
                receipts=[],
            ),
        )
        password = secrets.token_urlsafe(24)
        owned_secrets.append(password)
        encoded = hash_password(password)
        for key in ("demo_a", "demo_b", "demo_c", "demo_d", "demo_e", "demo_t"):
            AuthRepository(db).insert({"user_id": "users/" + key, "password_hash": encoded})
        db.collection("users").update({"_key": "demo_e", "roles": ["admin"]})
        private = db.collection("users").get("demo_t")["privacy"]
        db.collection("users").update(
            {
                "_key": "demo_t",
                "privacy": {**private, "employment_visible": False, "skills_visible": False},
            }
        )
        # More than one UI page, stored in real vertex/edge collections.
        base = demo_documents()["jobs"][0]
        for i in range(14):
            key = f"e2e_page_{i:02}"
            now = utc_now()
            db.collection("jobs").insert(
                {
                    **base,
                    "_key": key,
                    "title": f"E2E Pagination Engineer {i:02}",
                    "location": "Hanoi",
                    "work_mode": "onsite",
                    "created_at": now,
                    "updated_at": now,
                    "published_at": now,
                }
            )
            db.collection("job_at_company").insert(
                {
                    "_key": key,
                    "_from": "jobs/" + key,
                    "_to": "companies/demo_z",
                    "created_at": now,
                    "updated_at": now,
                }
            )
        runtime_password = secrets.token_urlsafe(40)
        owned_secrets.append(runtime_password)
        provision_runtime_user(config, username, runtime_password)
        user_created = True
        api_port, web_port = port(), port()
        env = {
            **os.environ,
            "ARANGO_URL": settings.url,
            "ARANGO_DATABASE": name,
            "APP_ARANGO_USERNAME": username,
            "APP_ARANGO_PASSWORD": runtime_password,
            "APP_JWT_SECRET": secrets.token_urlsafe(48),
            "APP_LOGIN_LIMIT": "100",
            "APP_REGISTER_LIMIT": "100",
            "JRN_E2E": "1",
            "JRN_E2E_PASSWORD": password,
            "JRN_E2E_PUBLIC_JOB": public_job.id,
            "JRN_E2E_PUBLIC_SOURCE": public_job.source.url,
            "JRN_E2E_BASE": f"http://127.0.0.1:{web_port}",
            "JRN_E2E_API": f"http://127.0.0.1:{api_port}",
            "API_PROXY_TARGET": f"http://127.0.0.1:{api_port}",
            "CI": "true",
        }
        for file, command, cwd in (
            (
                "backend.log",
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "backend.app:create_app",
                    "--factory",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(api_port),
                    "--no-access-log",
                    "--no-proxy-headers",
                ],
                ROOT,
            ),
            (
                "vite.log",
                [
                    shutil.which("node"),
                    "node_modules/vite/bin/vite.js",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(web_port),
                ],
                ROOT / "frontend",
            ),
        ):
            log = (artifacts / file).open("w", encoding="utf-8")
            logs.append(log)
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=cwd,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                )
            )
        wait_http(env["JRN_E2E_API"] + "/health/ready", processes[0])
        wait_http(env["JRN_E2E_BASE"], processes[1])
        print(f"Browser tests: real ArangoDB {version}; isolated DB; non-root runtime", flush=True)
        command = [
            shutil.which("node"),
            "node_modules/@playwright/test/cli.js",
            "test",
            *sys.argv[1:],
        ]
        result = subprocess.run(command, cwd=ROOT / "frontend", env=env, check=False)
        source = ROOT / "docs" / "reports" / f"{report_prefix}-playwright.json"
        if source.exists():
            report = json.loads(source.read_text(encoding="utf-8"))
            summary = {
                "database": f"ArangoDB {version}",
                "real_http": True,
                "non_root_runtime": True,
                "mock_business_data": False,
                "stats": report["stats"],
                "exit_code": result.returncode,
            }
            (ROOT / "docs" / "reports" / f"{report_prefix}-summary.json").write_text(
                json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        return result.returncode
    finally:
        for process in reversed(processes):
            stop(process)
        for log in logs:
            log.close()
        assert name == "jrn_e2e_" + suffix and username == "jrn_e2e_" + suffix
        if user_created:
            system.delete_user(username)
        system.delete_database(name)
        redact_artifacts(artifacts, report_prefix, owned_secrets)
        print("Owned test HTTP processes, database and runtime user removed")


if __name__ == "__main__":
    raise SystemExit(main())
