import httpx
import pytest
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.features.trends.models import NewsArticle, NewsArticleSection, CollectionRun
import pipelines.jobs.rss_history as history

XML = b'<rss><channel><item><title>News</title><link>https://example.com/1</link><pubDate>Wed, 18 Nov 2026 09:00:00 GMT</pubDate></item></channel></rss>'


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    for model in (NewsArticle, NewsArticleSection, CollectionRun):
        model.__table__.create(engine)
    yield engine
    engine.dispose()


def run(engine, response, feed="bbc-tech"):
    with httpx.Client(transport=httpx.MockTransport(lambda request: response)) as client:
        return history.execute_stored(engine, feed=feed, limit=5, timeout=2, client=client)


def test_window_and_sections_are_recorded(engine):
    xml = XML.replace(b'</channel>', b'<item><title>Old</title><link>https://example.com/2</link>'
                      b'<pubDate>Tue, 17 Nov 2026 09:00:00 GMT</pubDate></item></channel>')
    result = run(engine, httpx.Response(200, content=xml), feed="donga-politics")
    with Session(engine) as db:
        row = db.get(CollectionRun, result["run_id"])
        assert row.window_start_at.isoformat() == "2026-11-17T09:00:00"
        labels = db.scalars(select(NewsArticleSection.label)).all()
    assert labels == ["정치", "정치"]


def test_new_and_existing_counts(engine):
    first = run(engine, httpx.Response(200, content=XML))
    second = run(engine, httpx.Response(200, content=XML))
    assert (first["inserted_count"], first["existing_count"]) == (1, 0)
    assert (second["inserted_count"], second["existing_count"]) == (0, 1)
    with Session(engine) as db:
        runs = db.scalars(select(CollectionRun)).all()
        assert len(runs) == 2
        assert all(x.status == "success" and x.finished_at >= x.started_at for x in runs)


def test_429_has_unknown_counts_and_sanitized_error(engine):
    result = run(engine, httpx.Response(429, text="private credential"))
    with Session(engine) as db:
        row = db.get(CollectionRun, result["run_id"])
        assert row.status == "failed" and row.http_status == 429
        assert row.input_count is None
        assert row.error_code == "http_status"
    assert "private" not in str(result)


def test_partial_batch_does_not_store_articles(engine):
    xml = XML.replace(b'</channel>', b'<item><title>Invalid</title></item></channel>')
    result = run(engine, httpx.Response(200, content=xml))
    assert result["status"] == "partial"
    assert result["inserted_count"] == 0
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(NewsArticle)) == 0


def test_storage_failure_rolls_back_and_records_failure(engine, monkeypatch):
    original = history.store_news
    def broken(db, items):
        original(db, items)
        raise SQLAlchemyError("private SQL parameters")
    monkeypatch.setattr(history, "store_news", broken)
    result = run(engine, httpx.Response(200, content=XML))
    with Session(engine) as db:
        assert db.scalar(select(func.count()).select_from(NewsArticle)) == 0
        row = db.get(CollectionRun, result["run_id"])
        assert row.status == "failed" and row.error_code == "database_write"
        assert row.inserted_count == 0 and row.accepted_count == 1


def test_database_error_number_is_recorded_without_message(engine, monkeypatch):
    from sqlalchemy.exc import OperationalError
    class DriverError(Exception):
        pass
    def deadlock(db, items):
        raise OperationalError("private SQL", {}, DriverError(1213, "private message"))
    monkeypatch.setattr(history, "store_news", deadlock)
    result = run(engine, httpx.Response(200, content=XML))
    assert result["error_code"] == "database_write_1213"
    assert "private" not in str(result)


def test_recovers_only_same_owner_feed_running(engine):
    with Session(engine) as db, db.begin():
        for run_id, owner, feed, status in [
            ('stale', history.owner_id(), 'bbc-tech', 'running'),
            ('other-machine', 'different', 'bbc-tech', 'running'),
            ('old-unknown', None, 'bbc-tech', 'running'),
            ('other-feed', history.owner_id(), 'sbs-latest', 'running'),
            ('completed', history.owner_id(), 'bbc-tech', 'success'),
        ]:
            db.add(CollectionRun(run_id=run_id, owner_id=owner, feed=feed,
                                 started_at=history.now(), status=status))
    result = run(engine, httpx.Response(200, content=XML))
    assert result['status'] == 'success'
    with Session(engine) as db:
        stale = db.get(CollectionRun, 'stale')
        assert stale.status == 'interrupted'
        assert stale.finished_at is not None
        assert stale.error_code == 'previous_process_interrupted'
        for key in ('other-machine', 'old-unknown', 'other-feed'):
            assert db.get(CollectionRun, key).status == 'running'
        assert db.get(CollectionRun, 'completed').status == 'success'


def test_active_lock_prevents_recovery(engine):
    from pipelines.jobs.collection_lock import collection_lock
    with Session(engine) as db, db.begin():
        db.add(CollectionRun(run_id='active', owner_id=history.owner_id(),
                             feed='bbc-tech', started_at=history.now(), status='running'))
    with collection_lock('bbc-tech'):
        assert history.execute_stored(engine, feed='bbc-tech', limit=5, timeout=2)['error_code'] == 'collection_busy'
    with Session(engine) as db:
        assert db.get(CollectionRun, 'active').status == 'running'
