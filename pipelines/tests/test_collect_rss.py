import json

import httpx

from pipelines.jobs.collect_rss import main

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from app.features.trends.models import NewsArticle, CollectionRun
import pipelines.jobs.collect_rss as job


def test_dry_run_and_invalid_options_never_request(capsys):
    def handler(request):
        raise AssertionError("Unexpected request")
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert main([], client=client) == 0
        assert json.loads(capsys.readouterr().out)["status"] == "dry_run"
        assert main(["--limit", "0", "--execute"], client=client) == 2


def test_mock_execution(capsys):
    xml = b'<rss><channel><item><title>News</title><link>https://example.com/1</link><pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>'
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=xml))) as client:
        assert main(["--execute"], client=client) == 0
    assert json.loads(capsys.readouterr().out)["accepted_count"] == 1


def test_store_requires_execute(capsys):
    assert main(["--store"]) == 2
    assert json.loads(capsys.readouterr().out)["error_code"] == "invalid_options"


def test_collection_storage_and_repeat_are_idempotent(monkeypatch, capsys):
    engine = create_engine("sqlite://")
    NewsArticle.__table__.create(engine)
    CollectionRun.__table__.create(engine)
    monkeypatch.setattr(job, "get_engine", lambda: engine)
    xml = b'<rss><channel><item><title>News</title><link>https://example.com/1</link><pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>'
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=xml))) as client:
        for _ in range(2):
            assert main(["--execute", "--store"], client=client) == 0
            assert json.loads(capsys.readouterr().out)["storage"] == "committed"
    with Session(engine) as session:
        assert session.scalar(select(func.count()).select_from(NewsArticle)) == 1
    engine.dispose()


def test_missing_database_configuration_prevents_request(monkeypatch, capsys):
    def missing():
        raise RuntimeError("private configuration")
    monkeypatch.setattr(job, "get_engine", missing)
    def forbidden(request):
        raise AssertionError("Must check configuration before collection")
    with httpx.Client(transport=httpx.MockTransport(forbidden)) as client:
        assert main(["--execute", "--store"], client=client) == 2
    output = capsys.readouterr().out
    assert "private" not in output
    assert json.loads(output)["error_code"] == "database_configuration"


def test_missing_table_fails_without_creating_it(monkeypatch, capsys):
    from sqlalchemy import inspect
    engine = create_engine("sqlite://")
    monkeypatch.setattr(job, "get_engine", lambda: engine)
    xml = b'<rss><channel><item><title>News</title><link>https://example.com/1</link><pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>'
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=xml))) as client:
        assert main(["--execute", "--store"], client=client) == 1
    assert json.loads(capsys.readouterr().out)["error_code"] == "database_write"
    assert inspect(engine).get_table_names() == []
    engine.dispose()


def test_selected_feed_is_requested_and_reported(capsys):
    def handler(request):
        assert request.url.host == "news.sbs.co.kr"
        assert request.url.path == "/news/newsflashRssFeed.do"
        return httpx.Response(200, content=b'<rss><channel/></rss>')
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert main(["--feed", "sbs-latest", "--execute"], client=client) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["source"] == "SBS 뉴스"
    assert output["accepted_count"] == 0
