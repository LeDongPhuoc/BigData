import os
from dataclasses import dataclass, replace
from pathlib import Path

from database.config import Settings


@dataclass(frozen=True)
class AppSettings:
    database: Settings
    jwt_secret: str
    jwt_issuer: str = "job-referral-network"
    jwt_audience: str = "job-referral-api"
    access_seconds: int = 900
    refresh_seconds: int = 604800
    referral_seconds: int = 604800
    login_limit: int = 10
    refresh_limit: int = 60
    register_limit: int = 30
    connection_limit: int = 20
    referral_limit: int = 10
    referrers_per_job: int = 3
    cors_origins: tuple[str, ...] = ()

    def __post_init__(self):
        if len(self.jwt_secret.encode()) < 32 or self.jwt_secret.startswith("replace-with"):
            raise ValueError("APP_JWT_SECRET must contain at least 32 bytes")
        if "*" in self.cors_origins:
            raise ValueError("CORS origins must be explicit")
        for name in (
            "access_seconds",
            "refresh_seconds",
            "referral_seconds",
            "login_limit",
            "refresh_limit",
            "register_limit",
            "connection_limit",
            "referral_limit",
            "referrers_per_job",
        ):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")

    @classmethod
    def load(cls):
        database = Settings.load()
        values = {}
        if Path(".env").exists():
            for line in Path(".env").read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.lstrip().startswith("#"):
                    name, value = line.split("=", 1)
                    values[name.strip()] = value.strip()
        values.update(os.environ)
        if values.get("APP_ARANGO_USERNAME") or values.get("APP_ARANGO_PASSWORD"):
            if not values.get("APP_ARANGO_USERNAME") or not values.get("APP_ARANGO_PASSWORD"):
                raise ValueError("Set both APP_ARANGO_USERNAME and APP_ARANGO_PASSWORD")
            database = replace(
                database,
                username=values["APP_ARANGO_USERNAME"],
                password=values["APP_ARANGO_PASSWORD"],
            )
        return cls(
            database=database,
            jwt_secret=values.get("APP_JWT_SECRET", ""),
            **{
                name: int(values.get(f"APP_{name.upper()}", default))
                for name, default in {
                    "access_seconds": 900,
                    "refresh_seconds": 604800,
                    "referral_seconds": 604800,
                    "login_limit": 10,
                    "refresh_limit": 60,
                    "register_limit": 30,
                    "connection_limit": 20,
                    "referral_limit": 10,
                    "referrers_per_job": 3,
                }.items()
            },
            cors_origins=tuple(filter(None, values.get("APP_CORS_ORIGINS", "").split(","))),
        )
