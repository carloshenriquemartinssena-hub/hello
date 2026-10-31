import pytest
from fastapi.testclient import TestClient

from crm.main import create_app


@pytest.fixture
def app(tmp_path, monkeypatch):
    for key in ["CRM_ENV", "CRM_ADMIN_PASSWORD", "CRM_SESSION_SECRET", "CRM_WORKER_TOKEN"]:
        monkeypatch.delenv(key, raising=False)
    app = create_app("sqlite:///" + str(tmp_path / "test.db"))
    yield app
    app.state.engine.dispose()


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client
