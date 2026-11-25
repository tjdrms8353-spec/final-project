"""pytest 공통 설정 — 테스트용 격리 SQLite DB를 사용한다."""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

_tmp = tempfile.mkdtemp(prefix="dayribbon_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["SEED_DEMO"] = "1"
# 스케줄러가 테스트 중 즉시 돌지 않도록 큰 간격 지정
os.environ["AUTO_ANALYSIS_INTERVAL_SEC"] = "86400"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def owner_headers(client):
    r = client.post("/api/auth/login",
                    json={"email": "owner@dayribbon.demo", "password": "demo1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="session")
def viewer_headers(client):
    r = client.post("/api/auth/login",
                    json={"email": "viewer@dayribbon.demo", "password": "demo1234"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
