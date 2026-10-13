"""Explicit configuration. Environment overrides the optional local .env file."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    url: str
    database: str
    username: str
    password: str

    @classmethod
    def load(cls, env_file: Path = Path(".env")) -> "Settings":
        values = {}
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    key, value = line.split("=", 1)
                    values[key.strip()] = value.strip()
        values.update(os.environ)
        password = values.get("ARANGO_PASSWORD", "")
        if not password:
            raise ValueError("Set ARANGO_PASSWORD in environment or .env")
        return cls(
            url=values.get("ARANGO_URL", "http://127.0.0.1:8529"),
            database=values.get("ARANGO_DATABASE", "job_referral"),
            username=values.get("ARANGO_USERNAME", "root"),
            password=password,
        )
