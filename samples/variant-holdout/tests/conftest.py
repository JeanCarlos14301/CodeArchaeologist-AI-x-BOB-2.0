import sys
from pathlib import Path

import pytest

_parent = Path(__file__).resolve().parent.parent
SAMPLE = _parent if (_parent / "app.py").exists() else _parent / "samples" / "variant-holdout"
sys.path.insert(0, str(SAMPLE))

from app import create_app
from db import connect
from seed import seed


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "sample.sqlite3"
    seed(path)
    return path


@pytest.fixture
def client(database):
    app = create_app({"TESTING": True, "DATABASE": str(database)})
    return app.test_client()


@pytest.fixture
def login(client):
    def do_login(username="ana", password="DemoAna!2024"):
        return client.post("/login", data={"username": username, "password": password})
    return do_login
