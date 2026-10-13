import secrets
from dataclasses import replace
from uuid import uuid4

import pytest
from arango import ArangoClient
from arango.exceptions import CollectionCreateError, DocumentInsertError
from fastapi.testclient import TestClient

from backend.app import create_app
from backend.core.provisioning import provision_runtime_user
from database.connection import connect
from database.migrate import validate_schema

pytestmark = pytest.mark.integration


def test_runtime_user_runs_http_transactions_graph_but_cannot_mutate_schema(
    settings, db, api_config
):
    username, password = "jrn_runtime_test_" + uuid4().hex, secrets.token_urlsafe(48)
    target = replace(settings, database=db.name)
    system = ArangoClient(hosts=settings.url).db(
        "_system",
        username=settings.username,
        password=settings.password,
    )
    provision_runtime_user(target, username, password)
    try:
        runtime = connect(replace(target, username=username, password=password))
        validate_schema(runtime)
        with pytest.raises(CollectionCreateError) as error:
            runtime.create_collection("should_be_denied")
        assert error.value.http_code == 403
        with pytest.raises(DocumentInsertError) as error:
            runtime.collection("schema_migrations").insert({"_key": "forbidden"})
        assert error.value.http_code == 403
        assert not db.has_collection("should_be_denied")
        with TestClient(create_app(api_config, db=runtime)) as client:
            result = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "runtime@example.com",
                    "password": "A secure runtime passphrase!",
                    "display_name": "Runtime account",
                },
            )
            assert result.status_code == 201, result.text
            headers = {"Authorization": "Bearer " + result.json()["access_token"]}
            paths = client.get("/api/v1/graph/referral-paths?company_id=demo_x", headers=headers)
            assert paths.status_code == 200, paths.text
            assert client.get("/health/ready").status_code == 200
    finally:
        assert username.startswith("jrn_runtime_test_")
        system.delete_user(username)
