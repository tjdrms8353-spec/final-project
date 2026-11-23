import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.features.trends.schemas import NewsItem
from app.main import app


def test_sample_news_without_external_services(monkeypatch):
    import socket
    from app.db import session

    def forbid_external_access(*args, **kwargs):
        raise AssertionError("Sample news must not use the network or database")

    monkeypatch.setattr(session, "create_engine", forbid_external_access)
    with TestClient(app) as client:
        # Windows creates a local socket pair when starting the event loop.
        # Block network access only after that internal setup has completed.
        with monkeypatch.context() as request_patch:
            request_patch.setattr(socket.socket, "connect", forbid_external_access)
            response = client.get("/api/news/sample")
    assert response.status_code == 200
    payload = response.json()
    assert payload["data_source"] == "sample"
    assert payload["total"] == len(payload["items"]) == 3
    assert len({item["id"] for item in payload["items"]}) == 3
    timestamps = [item["published_at"] for item in payload["items"]]
    assert timestamps == sorted(timestamps, reverse=True)
    assert all(timestamp.endswith("Z") for timestamp in timestamps)


def test_sample_news_limit_does_not_change_total():
    with TestClient(app) as client:
        payload = client.get("/api/news/sample", params={"limit": 1}).json()
    assert len(payload["items"]) == 1
    assert payload["total"] == 3
    assert payload["items"][0]["id"] == "sample-001"


@pytest.mark.parametrize("limit", [0, -1, 101, "invalid"])
def test_invalid_limit_returns_422(limit):
    with TestClient(app) as client:
        response = client.get("/api/news/sample", params={"limit": limit})
    assert response.status_code == 422


def make_item(**overrides):
    return NewsItem.model_validate({
        "id": "sample-test",
        "title": "  샘플\n 뉴스  제목 ",
        "url": "https://example.com/sample-test",
        "source": " 샘플 뉴스 ",
        "published_at": "2026-01-01T09:00:00+09:00",
        **overrides,
    })


def test_text_and_timezone_normalization():
    item = make_item()
    assert item.title == "샘플 뉴스 제목"
    assert item.source == "샘플 뉴스"
    assert item.published_at.isoformat() == "2026-01-01T00:00:00+00:00"


@pytest.mark.parametrize("overrides", [
    {"title": " \n "},
    {"source": " "},
    {"url": "file:///sample.txt"},
    {"published_at": "2026-01-01T09:00:00"},
])
def test_invalid_news_is_rejected(overrides):
    with pytest.raises(ValidationError):
        make_item(**overrides)


def test_observation_time_does_not_become_publication_time():
    item = make_item(
        published_at=None, observed_at="2026-01-01T09:00:00+09:00",
    )
    payload = item.model_dump(mode="json")
    assert payload["published_at"] is None
    assert payload["observed_at"] == "2026-01-01T00:00:00Z"
    assert payload["summary"] == ""


def test_news_without_either_timestamp_is_rejected():
    with pytest.raises(ValidationError):
        make_item(published_at=None, observed_at=None)


def test_sample_response_exposes_raw_news_contract():
    with TestClient(app) as client:
        response = client.get("/api/news/sample", params={"limit": 1})
    assert response.status_code == 200
    payload = response.json()
    assert set(payload) == {"data_source", "items", "total"}
    assert set(payload["items"][0]) == {
        "id", "title", "url", "source", "published_at", "observed_at", "summary",
    }
    assert payload["items"][0]["observed_at"] is None
