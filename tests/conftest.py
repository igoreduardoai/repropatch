import pytest
from repropatch.config import Settings
from repropatch.api import create_app
from fastapi.testclient import TestClient

@pytest.fixture
def settings(tmp_path):return Settings(data_dir=tmp_path,auth_token='test-operator-token')

@pytest.fixture
def app(settings):return create_app(settings)

@pytest.fixture
def client(app):
    with TestClient(app) as c:
        c.headers.update({'Authorization':'Bearer test-operator-token'})
        yield c
