"""Provision a local runtime user once; preserve credentials and never print passwords."""

import secrets
from pathlib import Path

from backend.core.provisioning import provision_runtime_user
from database.config import Settings

path = Path(__file__).resolve().parents[1] / ".env"
values = dict(
    line.split("=", 1)
    for line in path.read_text(encoding="utf-8").splitlines()
    if line.strip() and not line.startswith("#")
)
if values.get("APP_ARANGO_USERNAME") or values.get("APP_ARANGO_PASSWORD"):
    if not values.get("APP_ARANGO_USERNAME") or not values.get("APP_ARANGO_PASSWORD"):
        raise ValueError("Incomplete runtime credentials; repair .env before provisioning")
    print("Runtime credentials already configured; unchanged")
else:
    username, password = "jrn_api", secrets.token_urlsafe(48)
    provision_runtime_user(Settings.load(), username, password)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(f"\nAPP_ARANGO_USERNAME={username}\nAPP_ARANGO_PASSWORD={password}\n")
    print("Provisioned non-root runtime user and stored local credentials in .env")
