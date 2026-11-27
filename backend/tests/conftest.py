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
# 스케줄러 비활성 — 첫 틱이 즉시 돌아 테스트 데이터와 경쟁하는 것을 방지
os.environ["SCHEDULER_ENABLED"] = "0"
os.environ["AUTO_ANALYSIS_INTERVAL_SEC"] = "86400"
os.environ["COLLECT_INTERVAL_SEC"] = "86400"
# 테스트 중 실제 외부 호출 차단 (수집기는 mock으로 검증)
os.environ["NEWS_COLLECT_ENABLED"] = "0"
os.environ["GDELT_ENABLED"] = "0"

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


@pytest.fixture()
def db(client):
    """앱 기동(client)으로 테이블이 생성된 뒤 세션을 연다."""
    from app.database import SessionLocal
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
