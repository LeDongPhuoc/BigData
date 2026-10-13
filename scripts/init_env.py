"""Create local credentials once, without printing or overwriting secrets."""

import secrets
from pathlib import Path

path = Path(__file__).resolve().parents[1] / ".env"
if path.exists():
    if "APP_JWT_SECRET=" not in path.read_text(encoding="utf-8"):
        with path.open("a", encoding="utf-8") as handle:
            handle.write(f"\nAPP_JWT_SECRET={secrets.token_urlsafe(48)}\n")
        print("Added random APP_JWT_SECRET; existing credentials unchanged")
    else:
        print(".env already contains credentials; unchanged")
else:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(
            "ARANGO_URL=http://127.0.0.1:8529\n"
            "ARANGO_DATABASE=job_referral\n"
            "ARANGO_USERNAME=root\n"
            f"ARANGO_PASSWORD={secrets.token_urlsafe(32)}\n"
            f"APP_JWT_SECRET={secrets.token_urlsafe(48)}\n"
        )
    print("Created local .env with a random password")
