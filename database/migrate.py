"""Forward-only, resumable migrations with checksums and a non-expiring lock."""

import hashlib
import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from arango.exceptions import DocumentInsertError

MIGRATIONS = Path(__file__).with_name("migrations")


class SchemaDriftError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def manifests(directory: Path = MIGRATIONS):
    result = []
    for path in sorted(directory.glob("[0-9][0-9][0-9]_*.json")):
        raw = path.read_bytes()
        data = json.loads(raw)
        result.append((data, hashlib.sha256(raw).hexdigest()))
    versions = [data["version"] for data, _ in result]
    if versions != list(range(1, len(result) + 1)) or not versions:
        raise SchemaDriftError("Migration versions must be contiguous from 1")
    return result


def _check_collection(db, name, spec):
    if not db.has_collection(name):
        raise SchemaDriftError(f"Missing collection {name}")
    properties = db.collection(name).properties()
    if properties["edge"] != spec["edge"]:
        raise SchemaDriftError(f"Incompatible collection type: {name}")
    actual_schema = dict(properties.get("schema") or {})
    # ArangoDB returns this implicit default although callers need not supply it.
    if actual_schema.get("type") == "json":
        actual_schema.pop("type")
    if actual_schema != spec["schema"]:
        raise SchemaDriftError(f"Schema drift in {name}; add an explicit migration")
    computed = properties.get("computedValues", []) or []
    if computed != spec.get("computed_values", []):
        raise SchemaDriftError(f"Computed values drift in {name}")


def _check_graph(db, spec):
    if not db.has_graph(spec["name"]):
        raise SchemaDriftError(f"Missing graph {spec['name']}")
    graph = db.graph(spec["name"])
    actual = sorted(graph.edge_definitions(), key=lambda d: d["edge_collection"])
    expected = sorted(spec["edge_definitions"], key=lambda d: d["edge_collection"])
    if actual != expected or sorted(graph.properties()["orphan_collections"]) != sorted(
        spec["orphan_collections"]
    ):
        raise SchemaDriftError("Named graph definitions drift")


def _check_index(db, collection, index):
    matches = [i for i in db.collection(collection).indexes() if i["name"] == index["name"]]
    if not matches or any(matches[0].get(key) != value for key, value in index.items()):
        raise SchemaDriftError(f"Missing/incompatible index {collection}.{index['name']}")


def validate_schema(db, directory: Path = MIGRATIONS):
    entries = manifests(directory)
    if not db.has_collection("schema_migrations"):
        raise SchemaDriftError("Migration history is missing")
    expected = {str(data["version"]): digest for data, digest in entries}
    rows = {row["_key"]: row for row in db.collection("schema_migrations").all()}
    if rows.keys() != expected.keys() or any(
        row.get("status") != "applied" or row.get("checksum") != expected[key]
        for key, row in rows.items()
    ):
        raise SchemaDriftError("Migration history is incomplete or checksum differs")
    _validate_state(db, _schema_state(entries))


def _schema_state(entries):
    state = {"collections": {}, "indexes": {}, "graph": None}
    for data, _ in entries:
        for name, spec in data.get("collections", {}).items():
            if name in state["collections"]:
                raise SchemaDriftError("Use schema_updates to alter an existing collection")
            state["collections"][name] = deepcopy(spec)
        for name, change in data.get("schema_updates", {}).items():
            if (
                name not in state["collections"]
                or state["collections"][name]["schema"] != change["before"]
            ):
                raise SchemaDriftError(f"Invalid schema update chain for {name}")
            if change["after"].get("level") != "strict":
                raise SchemaDriftError("Schema updates must keep strict validation")
            state["collections"][name]["schema"] = deepcopy(change["after"])
        if "graph" in data:
            state["graph"] = data["graph"]
        for name, indexes in data.get("indexes", {}).items():
            state["indexes"].setdefault(name, {}).update({i["name"]: i for i in indexes})
    return state


def _validate_state(db, state, resumable_updates=None):
    for name, spec in state["collections"].items():
        try:
            _check_collection(db, name, spec)
        except SchemaDriftError:
            change = (resumable_updates or {}).get(name)
            if not change:
                raise
            _check_collection(db, name, {**spec, "schema": change["after"]})
    if state["graph"]:
        _check_graph(db, state["graph"])
    for name, indexes in state["indexes"].items():
        for index in indexes.values():
            _check_index(db, name, index)


def _apply(db, data):
    # DDL is not transactional. Every step is create-if-missing and validates existing state.
    for name, spec in data.get("collections", {}).items():
        if not db.has_collection(name):
            db.create_collection(
                name,
                edge=spec["edge"],
                schema=spec["schema"],
                computedValues=spec.get("computed_values"),
            )
        _check_collection(db, name, spec)
    for name, change in data.get("schema_updates", {}).items():
        schema = dict(db.collection(name).properties()["schema"])
        schema.pop("type", None)
        if schema not in (change["before"], change["after"]):
            raise SchemaDriftError(f"Schema update precondition failed for {name}")
        invalid = list(
            db.aql.execute(
                "FOR doc IN @@collection FILTER !SCHEMA_VALIDATE(doc, @schema).valid "
                "LIMIT 1 RETURN doc._key",
                bind_vars={"@collection": name, "schema": change["after"]},
                fail_on_warning=True,
                max_runtime=60,
            )
        )
        if invalid:
            raise SchemaDriftError(
                f"Existing data violates new schema in {name}; migrate data first"
            )
        if schema != change["after"]:
            db.collection(name).configure(schema=change["after"])
    if "graph" in data:
        spec = data["graph"]
        if not db.has_graph(spec["name"]):
            db.create_graph(**spec)
        _check_graph(db, spec)
    for name, indexes in data.get("indexes", {}).items():
        for index in indexes:
            existing = db.collection(name).indexes()
            if not any(i["name"] == index["name"] for i in existing):
                db.collection(name).add_index(index)
            _check_index(db, name, index)


def migrate(db, directory: Path = MIGRATIONS):
    expected = manifests(directory)
    _schema_state(expected)  # validate all schema transition preconditions before DDL
    for name in ("schema_migrations", "migration_locks"):
        if not db.has_collection(name):
            db.create_collection(name)
    locks = db.collection("migration_locks")
    owner = uuid4().hex
    try:
        locks.insert({"_key": "schema", "owner": owner, "started_at": utc_now()})
    except DocumentInsertError as error:
        if error.error_code == 1210:
            raise RuntimeError(
                "Migration lock exists. Confirm the previous process stopped, then use unlock."
            ) from error
        raise
    journal = db.collection("schema_migrations")
    try:
        known = {str(data["version"]): digest for data, digest in expected}
        for row in journal.all():
            if row["_key"] not in known or row.get("checksum") != known[row["_key"]]:
                raise SchemaDriftError(
                    "Migration history/checksum mismatch; immutable files changed"
                )
        applied = []
        pending = None
        for entry in expected:
            row = journal.get(str(entry[0]["version"]))
            if row and row["status"] == "applied":
                if pending:
                    raise SchemaDriftError("Migration history contains a gap")
                applied.append(entry)
            elif pending is None:
                pending = entry[0]
        _validate_state(
            db, _schema_state(applied), pending.get("schema_updates", {}) if pending else None
        )
        for data, digest in expected:
            key = str(data["version"])
            record = journal.get(key)
            if record and record["status"] == "applied":
                continue
            journal.insert(
                {
                    "_key": key,
                    "checksum": digest,
                    "status": "applying",
                    "description": data["description"],
                    "started_at": utc_now(),
                },
                overwrite=True,
            )
            try:
                _apply(db, data)
            except Exception:
                journal.update({"_key": key, "status": "failed", "failed_at": utc_now()})
                raise
            journal.update({"_key": key, "status": "applied", "applied_at": utc_now()})
        validate_schema(db, directory)
        return [data["version"] for data, _ in expected]
    finally:
        # No TTL auto-unlock: a slow live migration must never lose its lock.
        record = locks.get("schema")
        if record and record["owner"] == owner:
            locks.delete(record, check_rev=True)
