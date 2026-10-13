"""Adversarial regression cases against the real migrated ArangoDB fixture."""

import asyncio
import re
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.http_limits import RequestLimits
from database.migrate import SchemaDriftError

pytestmark = pytest.mark.integration


def test_public_profile_does_not_disclose_private_salary_preferences(client, login):
    owner, viewer = login("demo_a"), login("demo_b")
    me = client.get("/api/v1/users/me", headers=owner)
    salary = {"salary_min": 12345678, "salary_max": 23456789}
    saved = client.patch(
        "/api/v1/profiles/me",
        headers={**owner, "If-Match": me.headers["ETag"]},
        json={**me.json()["profile"], **salary},
    )
    assert saved.status_code == 200, saved.text
    assert (
        client.get("/api/v1/profiles/me", headers=owner).json()["profile"]["salary_min"]
        == salary["salary_min"]
    )
    shared = client.get("/api/v1/users/demo_a/profile", headers=viewer)
    assert shared.status_code == 200, shared.text
    assert shared.json()["profile"]["salary_min"] is None
    assert shared.json()["profile"]["salary_max"] is None
    assert "email" not in shared.json()


def test_backend_rejects_oversized_and_chunked_bodies_before_parsing(client, db):
    before = db.collection("rate_limits").count()
    payload = b'{"email":"x@example.com","password":"' + b"x" * 131073 + b'"}'
    declared = client.post("/api/v1/auth/login", content=payload)
    assert declared.status_code == 413, declared.text[:200]
    chunked = client.post("/api/v1/auth/login", content=iter([payload[:65536], payload[65536:]]))
    assert chunked.status_code == 413, chunked.text[:200]
    for result in (declared, chunked):
        assert result.json()["error"]["code"] == "request_too_large"
        assert result.headers["Cache-Control"] == "no-store"
        assert result.headers["X-Request-ID"]
    assert db.collection("rate_limits").count() == before


def test_startup_rejects_unapplied_and_tampered_migration_history(db, api_config):
    journal = db.collection("schema_migrations")
    row = journal.get("3")
    for change in ({"status": "failed"}, {"checksum": "0" * 64}):
        journal.update({"_key": "3", **change})
        with pytest.raises(SchemaDriftError, match="Migration"):
            with TestClient(create_app(api_config, db=db)):
                pass
        journal.replace(row, check_rev=False)
    journal.delete("3")
    with pytest.raises(SchemaDriftError, match="Migration"):
        with TestClient(create_app(api_config, db=db)):
            pass


def test_every_protected_operation_rejects_anonymous_requests(client):
    spec = client.get("/openapi.json").json()
    checked = 0
    for path, operations in spec["paths"].items():
        for method, operation in operations.items():
            if not operation.get("security"):
                continue
            target = re.sub(r"\{[^}]+\}", "demo_a", path)
            result = client.request(method, target, json={} if method != "get" else None)
            assert result.status_code == 401, (method, path, result.status_code, result.text)
            assert result.headers["Cache-Control"] == "no-store"
            checked += 1
    assert checked >= 60


def test_nonfinite_salary_rejected_without_database_write(client, login, db):
    actor = login()
    me = client.get("/api/v1/users/me", headers=actor)
    before = db.collection("users").get("demo_a")["_rev"]
    with TestClient(client.app, raise_server_exceptions=False) as transport:
        result = transport.patch(
            "/api/v1/profiles/me",
            headers={**actor, "If-Match": me.headers["ETag"], "Content-Type": "application/json"},
            content='{"salary_min":Infinity,"salary_max":Infinity}',
        )
    assert result.status_code == 422, result.text
    assert "Infinity" not in result.text
    assert db.collection("users").get("demo_a")["_rev"] == before


def test_http_runtime_refuses_operator_root_credentials(api_config):
    with pytest.raises(ValueError, match="non-root"):
        create_app(api_config)


def test_active_listing_queries_use_new_indexes(db):
    for collection in ("companies", "skills"):
        plan = db.aql.explain(
            "FOR d IN @@collection FILTER d.status == @status "
            "SORT d.created_at DESC,d._key ASC LIMIT 0,21 RETURN d",
            bind_vars={"@collection": collection, "status": "active"},
        )
        used = {i["name"] for n in plan["nodes"] for i in n.get("indexes", [])}
        assert collection + "_status_created" in used, used
        assert not any(n["type"] == "EnumerateCollectionNode" for n in plan["nodes"])


def test_refresh_has_persisted_quota_and_does_not_write_on_denial(client, db):
    client.app.state.config = replace(client.app.state.config, refresh_limit=1)
    payload = {"refresh_token": "0" * 32 + "." + "x" * 48}
    assert client.post("/api/v1/auth/refresh", json=payload).status_code == 401
    assert client.post("/api/v1/auth/refresh", json=payload).status_code == 429
    rows = list(db.aql.execute("FOR r IN rate_limits FILTER r.operation == 'refresh' RETURN r"))
    assert len(rows) == 1 and rows[0]["count"] == 1
    assert db.collection("auth_sessions").count() == 0


def test_body_deadline_and_admission_release_against_real_asgi_app(client):
    async def exercise():
        guard = RequestLimits(client.app, active_limit=1, body_seconds=0.15)
        held, release = asyncio.Event(), asyncio.Event()
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/health/ready",
            "raw_path": b"/health/ready",
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 1000),
            "server": ("test", 80),
            "state": {"request_id": "admission-review"},
        }

        async def stalled():
            held.set()
            await release.wait()
            return {"type": "http.request", "body": b"", "more_body": False}

        first, denied, healthy = [], [], []

        async def first_send(message):
            first.append(message)

        async def denied_send(message):
            denied.append(message)

        async def healthy_send(message):
            healthy.append(message)

        task = asyncio.create_task(guard(scope, stalled, first_send))
        await held.wait()
        await guard(scope, stalled, denied_send)
        assert denied[0]["status"] == 503
        await task
        assert first[0]["status"] == 408
        assert guard.active == 0
        release.set()
        await guard(scope, stalled, healthy_send)
        assert healthy[0]["status"] == 200  # Real ArangoDB readiness after release.
        assert guard.active == 0

    asyncio.run(exercise())
