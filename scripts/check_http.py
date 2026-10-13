"""Read-only smoke check against the actual TCP HTTP server, never ASGI mocks."""

import json
import urllib.error
import urllib.request
from pathlib import Path

from database.migrate import utc_now

BASE = "http://127.0.0.1:8000"


def get(path):
    try:
        response = urllib.request.urlopen(BASE + path, timeout=10)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        return (
            response.status,
            json.loads(response.read()),
            {name.lower(): value for name, value in response.headers.items()},
        )


def main():
    checks = {}
    for path, expected in (
        ("/health/live", 200),
        ("/health/ready", 200),
        ("/api/v1/jobs", 401),
        ("/missing", 404),
    ):
        status, body, headers = get(path)
        assert status == expected, (path, status)
        assert headers.get("cache-control") == "no-store"
        assert headers.get("x-request-id")
        if status >= 400:
            assert body["error"]["request_id"] == headers["x-request-id"]
        checks[path] = status
    status, schema, _ = get("/openapi.json")
    assert status == 200
    operations = sum(
        method in {"get", "post", "put", "patch", "delete"}
        for path in schema["paths"].values()
        for method in path
    )
    expected_schema = json.loads(Path("docs/api.openapi.json").read_text(encoding="utf-8"))
    assert schema == expected_schema, "Runtime OpenAPI differs from committed API contract"
    report = {
        "checked_at": utc_now(),
        "base_url": BASE,
        "transport": "TCP HTTP",
        "checks": checks,
        "operations": operations,
        "openapi_matches_export": True,
    }
    Path("docs/reports/backend-http.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
