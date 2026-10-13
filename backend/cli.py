"""Operator-only bootstrap: passwords are read from the terminal, never CLI arguments."""

import argparse
import getpass
from uuid import uuid4

from backend.core.config import AppSettings
from backend.core.provisioning import provision_runtime_user
from backend.core.security import hash_password
from backend.core.transactions import transaction
from backend.core.workflow import audit
from backend.modules.auth.repository import AuthRepository
from backend.modules.auth.schemas import Register
from backend.modules.users.repository import UserRepository
from backend.modules.users.schemas import Privacy, Profile
from database.config import Settings
from database.connection import connect
from database.migrate import validate_schema


def main():
    parser = argparse.ArgumentParser(description="Bootstrap an administrator in real ArangoDB")
    parser.add_argument("command", choices=["create-admin", "provision-db-user"])
    parser.add_argument("--email")
    parser.add_argument("--username")
    parser.add_argument("--display-name", default="Administrator")
    args = parser.parse_args()
    if args.command == "provision-db-user":
        if not args.username:
            parser.error("--username is required")
        password = getpass.getpass("New runtime database password (at least 32 characters): ")
        if password != getpass.getpass("Repeat password: "):
            parser.error("Passwords do not match")
        provision_runtime_user(Settings.load(), args.username, password)
        print("Runtime database user created with collection grants; no DDL privileges")
        return
    if not args.email:
        parser.error("--email is required")
    password = getpass.getpass("New administrator password (12–128 characters): ")
    if password != getpass.getpass("Repeat password: "):
        parser.error("Passwords do not match")
    data = Register(email=args.email, password=password, display_name=args.display_name)
    config = AppSettings.load()
    db = connect(config.database)
    validate_schema(db)
    encoded = hash_password(data.password)
    with transaction(db) as tx:
        repo = UserRepository(tx)
        if repo.by_email(data.email):
            parser.error("Email already exists; bootstrap will not elevate an existing account")
        user = repo.insert(
            {
                "email": data.email,
                "display_name": data.display_name,
                "roles": ["admin"],
                "status": "active",
                "deleted_at": None,
                "privacy": Privacy(
                    discoverable=False,
                    allow_in_paths=False,
                    employment_visible=False,
                    skills_visible=False,
                ).model_dump(),
                "profile": Profile().model_dump(),
            }
        )
        AuthRepository(tx).insert({"user_id": user["_id"], "password_hash": encoded})
        audit(tx, user["_id"], "operator.create_admin", user["_id"], uuid4().hex)
    print(f"Created administrator {user['_key']}")


if __name__ == "__main__":
    main()
