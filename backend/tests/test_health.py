from fastapi.testclient import TestClient
import pytest

from app.core.config import get_settings
from app.db import session


def test_health_without_database(monkeypatch):
    for key in ("TIDB_HOST", "TIDB_USER", "TIDB_PASSWORD", "TIDB_DATABASE"):
        monkeypatch.setenv(key, "")
    get_settings.cache_clear()


    def forbid_database(*args, **kwargs):
        raise AssertionError("Health must not initialize a database connection")

    monkeypatch.setattr(session, "create_engine", forbid_database)
    from app.main import app

    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    get_settings.cache_clear()


@pytest.mark.parametrize("path,feature", [
    ("/api/news/status", "trends"),
    ("/api/finance/status", "finance"),
    ("/api/erp/status", "receipts"),
    ("/api/v1/trends/status", "trends"),
    ("/api/v1/finance/status", "finance"),
    ("/api/v1/receipts/status", "receipts"),
])
def test_feature_route_compatibility(path, feature):
    from app.main import app

    with TestClient(app) as client:
        response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"feature": feature, "status": "not_implemented"}
