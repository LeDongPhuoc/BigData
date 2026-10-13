"""Operator infrastructure; separate from HTTP authorization and runtime credentials."""

import re

from arango import ArangoClient

from backend.core.transactions import DOMAIN_COLLECTIONS


def provision_runtime_user(settings, username, password):
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{2,63}", username) or username == "root":
        raise ValueError("Choose a non-root database username (3–64 characters)")
    if len(password) < 32:
        raise ValueError("Runtime database password must contain at least 32 characters")
    system = ArangoClient(hosts=settings.url).db(
        "_system",
        username=settings.username,
        password=settings.password,
    )
    system.create_user(username, password=password, active=True)
    try:
        system.update_permission(username, "none", "*")
        system.update_permission(username, "none", "_system")
        system.update_permission(username, "ro", settings.database)
        system.update_permission(username, "ro", settings.database, "*")
        # ArangoDB derives system-collection permissions from database access;
        # its API explicitly rejects collection grants for _graphs.
        for collection in DOMAIN_COLLECTIONS:
            system.update_permission(
                username,
                "rw",
                settings.database,
                collection,
            )
    except BaseException:
        # This invocation created the user; never delete or modify pre-existing users.
        system.delete_user(username)
        raise
