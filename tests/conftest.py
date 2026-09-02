import os
import tempfile

import pytest

import database.db as db_module
from app import app as flask_app
from database.db import init_db, seed_db


@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    os.close(db_fd)
    db_module.DB_PATH = db_path

    flask_app.config.update(TESTING=True)

    with flask_app.app_context():
        init_db()
        seed_db()

    yield flask_app

    try:
        os.unlink(db_path)
    except PermissionError:
        pass


@pytest.fixture
def client(app):
    return app.test_client()
