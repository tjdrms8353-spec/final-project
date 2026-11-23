import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.features.trends.router import news_db
from app.features.trends.models import CollectionRun, NewsArticle, NewsTranslation
from app.features.trends.repository import store_news
from app.features.trends.schemas import NewsItem


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    NewsArticle.__table__.create(engine)
    CollectionRun.__table__.create(engine)
    NewsTranslation.__table__.create(engine)
    with Session(engine) as db, db.begin():
        store_news(db, [NewsItem(
            id=str(i), title=title, source=source, url=f"https://example.com/{i}",
            observed_at=f"2026-11-18T0{i}:00:00Z",
        ) for i, title, source in [(1, "AI growth 10%", "A"), (2, "AI research", "B"), (3, "Other news", "A")]])
    def override():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[news_db] = override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(news_db, None)
        engine.dispose()


def test_list_paging_and_detail(client):
    response = client.get("/api/news", params={"limit": 1, "offset": 1})
    assert response.status_code == 200
    data = response.json()
    assert (data["data_source"], data["total"], data["limit"], data["offset"]) == ("database", 3, 1, 1)
    item = data["items"][0]
    assert item["id"] == "2"
    assert item["published_at"] is None
    assert item["observed_at"].endswith("Z")
    assert client.get('/api/news/' + item['article_id']).json() == item
    assert client.get("/api/news", params={"offset": 10}).json()["items"] == []


@pytest.mark.parametrize("params,total", [
    ({"q": "AI"}, 2), ({"source": "A"}, 2), ({"q": "AI", "source": "A"}, 1),
    ({"q": "%"}, 1), ({"q": "_"}, 0), ({"q": "' OR 1=1 --"}, 0),
])
def test_filters_and_literal_search(client, params, total):
    response = client.get("/api/news", params=params)
    assert response.status_code == 200
    assert response.json()["total"] == total


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"q": "a" * 201}])
def test_invalid_query(client, params):
    assert client.get("/api/news", params=params).status_code == 422


def test_missing_and_static_routes(client):
    assert client.get("/api/news/" + "0" * 64).status_code == 404
    assert client.get("/api/news/bad-id").status_code == 422
    assert client.get("/api/news/sample").json()["data_source"] == "sample"
    assert client.get("/api/news/status").status_code == 200


def test_coverage_route(client):
    response = client.get("/api/news/coverage", params={"hours": 24})
    assert response.status_code == 200
    assert response.json()["gaps"] == []
    assert client.get("/api/news/coverage", params={"hours": 0}).status_code == 422
    assert client.get("/api/news/coverage", params={"hours": 721}).status_code == 422


def test_database_error_is_sanitized(monkeypatch):
    import app.features.trends.router as router
    def unavailable():
        raise RuntimeError("private-password")
        yield
    monkeypatch.setattr(router, "get_db", unavailable)
    with TestClient(app) as client:
        response = client.get("/api/news")
    assert response.status_code == 503
    assert "private" not in response.text
