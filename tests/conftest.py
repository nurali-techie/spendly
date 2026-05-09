import os
import tempfile
import pytest
import database.db as db_module
from app import app


@pytest.fixture
def client():
    db_fd, db_path = tempfile.mkstemp()
    db_module.DB_PATH = db_path
    with app.app_context():
        db_module.init_db()
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as client:
        yield client
    os.close(db_fd)
    os.unlink(db_path)
