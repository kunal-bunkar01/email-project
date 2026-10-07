import os
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp(prefix="sable-test-"))
os.environ["DATABASE_URL"] = "sqlite:///" + (_tmp / "test.db").as_posix()
os.environ["DEMO_MODE"] = "true"
os.environ["EMAIL_POLL_ENABLED"] = "false"
os.environ["OPENAI_API_KEY"] = ""
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client
