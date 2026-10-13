from dataclasses import replace
from uuid import uuid4

import pytest
from arango import ArangoClient

from database.config import Settings
from database.connection import connect
from database.migrate import migrate
from database.seed import seed


@pytest.fixture(scope="session")
def settings():
    config = Settings.load()
    # A real connectivity failure fails the suite, never skips or substitutes mocks.
    client = ArangoClient(hosts=config.url)
    system = client.db("_system", username=config.username, password=config.password)
    assert system.version().startswith("3.12.")
    return config


@pytest.fixture
def empty_db(settings):
    name = "jrn_test_" + uuid4().hex
    system = ArangoClient(hosts=settings.url).db(
        "_system", username=settings.username, password=settings.password
    )
    db = connect(replace(settings, database=name), create=True)
    try:
        yield db
    finally:
        assert name.startswith("jrn_test_") and len(name) == len("jrn_test_") + 32
        system.delete_database(name)


@pytest.fixture
def db(empty_db):
    migrate(empty_db)
    seed(empty_db)
    return empty_db
