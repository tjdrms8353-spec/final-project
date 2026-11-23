from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.features.trends.models import CollectionRun, NewsArticle, NewsArticleSection, NewsTranslation
from app.features.trends.repository import (
    collection_gaps, find_news, list_news, search_news, store_news, store_sections, url_hash,
)
from app.features.trends.schemas import NewsItem


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    for model in (NewsArticle, NewsArticleSection, CollectionRun, NewsTranslation):
        model.__table__.create(engine)
    yield engine
    engine.dispose()


def article(**changes):
    return NewsItem.model_validate({
        "id": "rss-1", "title": "News", "url": "https://example.com/1",
        "source": "Example", "observed_at": "2026-11-18T09:00:00+09:00",
        **changes,
    })


def test_repeat_and_cross_source_url_keep_first_version(engine):
    with Session(engine) as session:
        store_news(session, [article(), article(id="gdelt-2", title="Changed", url="https://EXAMPLE.com:443/1#part")])
        session.commit()
    with Session(engine) as session:
        store_news(session, [article()])
        session.commit()
        assert session.scalar(select(func.count()).select_from(NewsArticle)) == 1
        news = list_news(session)[0]
        assert news.id == "rss-1"
        assert news.title == "News"
        assert news.published_at is None
        assert news.observed_at.isoformat() == "2026-11-18T00:00:00+00:00"


def test_caller_can_rollback(engine):
    with Session(engine) as session:
        store_news(session, [article()])
        session.rollback()
        assert list_news(session) == []


def test_sort_pagination_and_distinct_query_urls(engine):
    with Session(engine) as session:
        store_news(session, [article(), article(id="2", url="https://example.com/1?v=2", observed_at="2026-11-18T01:00:00Z")])
        assert list_news(session, limit=1)[0].id == "2"
        assert list_news(session, limit=1, offset=1)[0].id == "rss-1"
        assert list_news(session, offset=2) == []


def test_empty_summary_is_filled_once(engine):
    with Session(engine) as session:
        store_news(session, [article()])
        store_news(session, [article(summary="first", title="Changed")])
        store_news(session, [article(summary="second")])
        session.commit()
        news = list_news(session)[0]
    assert (news.title, news.summary) == ("News", "first")


def test_korean_translation_is_joined(engine):
    item = article()
    with Session(engine) as session:
        store_news(session, [item, article(id="2", url="https://example.com/2")])
        session.add(NewsTranslation(url_hash=url_hash(item), lang="ko", title="뉴스", summary="",
                                    provider="deepl", translated_at=T0))
        session.commit()
        listed = {i.id: i for i in search_news(session).items}
        detail = find_news(session, url_hash(item))
    assert (listed["rss-1"].title_ko, listed["rss-1"].summary_ko) == ("뉴스", None)
    assert listed["2"].title_ko is None
    assert detail.title_ko == "뉴스" and detail.title == "News"


def test_sections_keep_first_feed_and_allow_multiple_labels(engine):
    item = article()
    seen = datetime(2026, 11, 19, tzinfo=timezone.utc)
    with Session(engine) as session:
        assert store_sections(session, [item], {item.id: ["정치"]}, "yna-politics", seen_at=seen) == 1
        assert store_sections(session, [item], {item.id: ["정치", "경제"]}, "yna-economy", seen_at=seen) == 1
        session.commit()
        rows = {(r.label, r.feed) for r in session.scalars(select(NewsArticleSection))}
    assert rows == {("정치", "yna-politics"), ("경제", "yna-economy")}


T0 = datetime(2026, 11, 19, 0, 0)


def add_runs(engine, *runs):
    with Session(engine) as session, session.begin():
        for i, (feed, minutes, window, status) in enumerate(runs):
            session.add(CollectionRun(
                run_id=str(i), feed=feed, status=status, started_at=T0 + timedelta(minutes=minutes),
                window_start_at=None if window is None else T0 + timedelta(minutes=window)))


def test_collection_gaps(engine):
    add_runs(engine,
             ("a", 0, -60, "success"), ("a", 5, -55, "success"),     # overlapping window: no gap
             ("a", 600, 500, "success"),                             # window starts after previous run: missed
             ("a", 605, None, "failed"),                             # failures are ignored
             ("b", 0, None, "success"), ("b", 30, None, "success"),  # undated, short interval: no gap
             ("b", 200, None, "success"))                            # undated, long interval: unverified
    utc = lambda minutes: (T0 + timedelta(minutes=minutes)).replace(tzinfo=timezone.utc)
    with Session(engine) as session:
        gaps = collection_gaps(session, since=utc(-1), now=utc(620))
    assert [(g.feed, g.kind, g.start, g.end) for g in gaps] == [
        ("a", "missed", utc(5), utc(500)),
        ("b", "unverified", utc(30), utc(200)),
        ("b", "ongoing", utc(200), None),
    ]
    with Session(engine) as session:
        assert [g.feed for g in collection_gaps(session, since=utc(-1), now=utc(620), feed="a")] == ["a"]


@pytest.mark.parametrize("options", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_invalid_pagination(engine, options):
    with Session(engine) as session, pytest.raises(ValueError):
        list_news(session, **options)
