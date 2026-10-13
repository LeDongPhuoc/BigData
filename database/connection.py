from arango import ArangoClient

from database.config import Settings


def connect(settings: Settings, create: bool = False):
    client = ArangoClient(hosts=settings.url, request_timeout=30)
    if create:
        system = client.db("_system", username=settings.username, password=settings.password)
        if not system.has_database(settings.database):
            system.create_database(settings.database)
    db = client.db(settings.database, username=settings.username, password=settings.password)
    version = db.version()
    if not version.startswith("3.12."):
        raise RuntimeError(f"Validated server family is ArangoDB 3.12; found {version}")
    return db
