import pytest
from fastapi.testclient import TestClient

from backend.app import create_app
from database.migrate import SchemaDriftError

pytestmark = pytest.mark.integration


def test_health_openapi_errors_cors_and_no_store(client):
    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").json() == {"status": "ready"}
    schema = client.get("/openapi.json").json()
    assert len(schema["paths"]) >= 50
    assert "HTTPBearer" in schema["components"]["securitySchemes"]
    unknown = client.get("/missing", headers={"X-Request-ID": "valid-request-id"})
    assert (
        unknown.status_code == 404 and unknown.json()["error"]["request_id"] == "valid-request-id"
    )
    assert unknown.headers["Cache-Control"] == "no-store"
    cors = client.options(
        "/api/v1/jobs",
        headers={"Origin": "https://untrusted.example", "Access-Control-Request-Method": "GET"},
    )
    assert "Access-Control-Allow-Origin" not in cors.headers


def test_startup_rejects_database_schema_drift(db, api_config):
    schema = db.collection("users").properties()["schema"]
    schema["level"] = "none"
    db.collection("users").configure(schema=schema)
    with pytest.raises(SchemaDriftError, match="Schema drift"):
        with TestClient(create_app(api_config, db=db)):
            pass
