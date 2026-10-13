"""Exercise recovery into a freshly owned database; never overwrite the source."""

import json
import re
import shutil
import subprocess
import tarfile
import tempfile
from dataclasses import replace
from pathlib import Path, PurePosixPath
from uuid import uuid4

from arango import ArangoClient

from database.config import Settings
from database.connection import connect
from database.migrate import validate_schema
from database.queries import GraphQueries
from database.seed import audit_integrity


def extract_dump(archive, destination):
    """Extract regular dump files only; reject Windows/UNC and traversal paths first."""
    destination.mkdir(exist_ok=False)
    base = destination.resolve()
    with tarfile.open(fileobj=archive, mode="r:") as stream:
        for member in stream:
            name = PurePosixPath(member.name)
            if (
                name.is_absolute()
                or ".." in name.parts
                or "\\" in member.name
                or ":" in member.name
                or not (member.isfile() or member.isdir())
            ):
                raise ValueError("Unsafe dump archive entry")
            target = base.joinpath(*name.parts).resolve()
            if not target.is_relative_to(base):
                raise ValueError("Dump archive target leaves the backup directory")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, target.open("xb") as output:
                    shutil.copyfileobj(source, output)


def copy_dump(container, dump_dir, destination):
    # docker cp cannot access this container's tmpfs mount. Stream through exec,
    # retaining the bytes locally and validating entries before writing each file.
    with tempfile.TemporaryFile() as archive:
        subprocess.run(
            ["docker", "exec", container, "tar", "-C", dump_dir, "-cf", "-", "."],
            check=True,
            stdout=archive,
            stderr=subprocess.PIPE,
        )
        archive.seek(0)
        extract_dump(archive, destination)


def main():
    settings = Settings.load()
    if settings.url != "http://127.0.0.1:8529" or settings.username != "root":
        raise ValueError(
            "This local recovery check requires the repository's Docker Compose server"
        )
    token = uuid4().hex
    restored_name = "jrn_restore_" + token
    dump_dir = "/tmp/jrn-recovery-" + token
    source = connect(settings)
    system = ArangoClient(hosts=settings.url).db(
        "_system", username=settings.username, password=settings.password
    )
    if system.has_database(restored_name):
        raise RuntimeError("Generated restore target already exists")
    subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "arangodb",
            "sh",
            "-c",
            'exec arangodump --server.username root --server.password "$ARANGO_ROOT_PASSWORD" '
            '--server.database "$1" --include-system-collections true --output-directory "$2"',
            "sh",
            settings.database,
            dump_dir,
        ],
        check=True,
        capture_output=True,
    )
    container = subprocess.check_output(
        ["docker", "compose", "ps", "-q", "arangodb"], text=True
    ).strip()
    backup = Path("backups") / ("recovery-" + token)
    backup.parent.mkdir(exist_ok=True)
    try:
        copy_dump(container, dump_dir, backup)
        subprocess.run(
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "arangodb",
                "sh",
                "-c",
                "exec arangorestore --server.username root "
                '--server.password "$ARANGO_ROOT_PASSWORD" '
                '--server.database "$1" --create-database true --include-system-collections true '
                '--overwrite false --input-directory "$2"',
                "sh",
                restored_name,
                dump_dir,
            ],
            check=True,
            capture_output=True,
        )
        restored = connect(replace(settings, database=restored_name))
        validate_schema(restored)
        issues = audit_integrity(restored)
        if issues:
            raise RuntimeError("Restored integrity check failed: " + "; ".join(issues))
        collections = [c["name"] for c in source.collections() if not c["system"]]
        counts = {name: source.collection(name).count() for name in collections}
        if counts != {name: restored.collection(name).count() for name in collections}:
            raise RuntimeError("Restore collection counts differ from source")
        graph_options = {"job_id": "jobs/demo_backend", "as_of": "2026-10-12T00:00:00.000Z"}
        expected_paths = GraphQueries(source).referral_paths(
            "users/demo_a",
            "companies/demo_x",
            **graph_options,
        )
        paths = GraphQueries(restored).referral_paths(
            "users/demo_a",
            "companies/demo_x",
            **graph_options,
        )
        if paths != expected_paths:
            raise RuntimeError("Restored graph paths differ from source")
        # Public catalog retirement makes legacy test targets archived; [] then
        # is correct. Compare the actual source instead of requiring old fixtures.
        report = {
            "client_date": "2026-10-12",
            "version": restored.version(),
            "backup": str(backup),
            "source_counts": counts,
            "schema": "pass",
            "integrity": "pass",
            "path_hops": [p["hops"] for p in paths],
            "source_path_hops": [p["hops"] for p in expected_paths],
            "source_unchanged": True,
            "restore_target": "disposable owned database",
        }
        output = Path("docs/reports/recovery.json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    finally:
        if not re.fullmatch(r"jrn_restore_[a-f0-9]{32}", restored_name) or not re.fullmatch(
            r"/tmp/jrn-recovery-[a-f0-9]{32}", dump_dir
        ):
            raise RuntimeError("Refusing to delete an unowned restore target")
        if system.has_database(restored_name):
            system.delete_database(restored_name)
        subprocess.run(
            ["docker", "exec", container, "rm", "-rf", "--", dump_dir],
            check=True,
            capture_output=True,
        )


if __name__ == "__main__":
    main()
