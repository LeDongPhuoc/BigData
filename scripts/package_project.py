"""Create a portable source/data ZIP without local environments or credentials."""

import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "dist" / "share" / "bigdata-source-vietjobs-2026-10-14.zip"
EXCLUDED_DIRS = {
    ".git", ".aws", ".codex", ".agents", ".venv", ".audit-venv",
    "venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", "build", "dist", "backups", "test-results",
    "playwright-report", ".idea",
}
TEXT_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".mjs", ".json", ".md",
                 ".txt", ".yaml", ".yml", ".toml", ".xml", ".html", ".ini"}
RAW = "DATA_/vietjobs-network/data/raw/vietjobs/VietJobs.csv"


def local_secrets():
    path = ROOT / ".env"
    if not path.exists():
        return []
    values = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.partition("=")
        if sep and any(word in key.upper() for word in ("PASSWORD", "SECRET", "TOKEN")):
            value = value.strip().strip("\"'")
            if len(value) >= 12:
                values.append(value.encode("utf-8"))
    return values


def files_to_share():
    stack = [ROOT]
    files = []
    while stack:
        directory = stack.pop()
        with os.scandir(directory) as entries:
            for entry in entries:
                info = entry.stat(follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                    continue  # Do not follow Windows junctions or other reparse points.
                name = entry.name
                if entry.is_dir(follow_symlinks=False):
                    if name not in EXCLUDED_DIRS and not name.endswith(".egg-info"):
                        stack.append(Path(entry.path))
                elif entry.is_file(follow_symlinks=False):
                    if ((name == ".env" or name.startswith(".env.")) and name != ".env.example"):
                        continue
                    if name.endswith((".pyc", ".pyo", ".tar", ".zip", ".7z", ".bak", ".pem", ".key")):
                        continue
                    files.append(Path(entry.path))
    return sorted(files)


def main():
    files = files_to_share()
    secrets = local_secrets()
    for path in files:
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {".env.example", "Dockerfile"}:
            contents = path.read_bytes()
            if any(secret in contents for secret in secrets):
                raise RuntimeError(f"Local credential found; package aborted: {path.relative_to(ROOT)}")
    relative = {path.relative_to(ROOT).as_posix() for path in files}
    required = {RAW, "compose.yaml", "database/seed.py", "requirements.lock",
                "frontend/package-lock.json", "docs/huong-dan-chay-ban-chia-se.md",
                "docker/build-wheels/setuptools-84.0.0-py3-none-any.whl"}
    if required - relative:
        raise RuntimeError(f"Missing required files: {sorted(required - relative)}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            archive.write(path, "bigdata/" + path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(OUTPUT) as archive:
        bad_file = archive.testzip()
        if bad_file:
            raise RuntimeError(f"ZIP CRC failed: {bad_file}")
        with archive.open("bigdata/" + RAW) as handle:
            raw_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    with (ROOT / RAW).open("rb") as handle:
        original_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    if raw_hash != original_hash:
        raise RuntimeError("Raw CSV hash changed in the ZIP")
    with OUTPUT.open("rb") as handle:
        archive_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    report = {
        "archive": str(OUTPUT), "bytes": OUTPUT.stat().st_size,
        "mib": round(OUTPUT.stat().st_size / 1024 ** 2, 2),
        "file_count": len(files), "source_bytes": sum(path.stat().st_size for path in files),
        "sha256": archive_hash, "raw_sha256": raw_hash,
        "crc_passed": True, "raw_matches_original": True,
        "local_credentials_scan_passed": True,
        "excluded_directories": sorted(EXCLUDED_DIRS),
        "contains_live_database": False,
    }
    OUTPUT.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
