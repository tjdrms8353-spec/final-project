import json

import httpx
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.features.trends.models import NewsArticle, NewsTranslation
from app.features.trends.repository import store_news
from app.features.trends.schemas import NewsItem
import pipelines.jobs.translate_news as job


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    NewsArticle.__table__.create(engine)
    NewsTranslation.__table__.create(engine)
    with Session(engine) as db:
        store_news(db, [
            NewsItem(id="b1", title="AI news", url="https://bbc.example/1", source="BBC News",
                     summary="Short summary", observed_at="2026-11-23T01:00:00Z"),
            NewsItem(id="b2", title="Chips", url="https://bbc.example/2", source="BBC News",
                     observed_at="2026-11-23T00:00:00Z"),
            NewsItem(id="k1", title="국내", url="https://kr.example/1", source="연합뉴스",
                     observed_at="2026-11-23T02:00:00Z"),
        ])
        db.commit()
    yield engine
    engine.dispose()


def deepl(calls):
    def handler(request):
        texts = json.loads(request.content)["text"]
        calls.append(texts)
        return httpx.Response(200, json={"translations": [{"text": f"KO:{t}"} for t in texts]})
    return httpx.Client(transport=httpx.MockTransport(handler))


def rows(engine):
    with Session(engine) as db:
        return {r.title: r.summary for r in db.scalars(select(NewsTranslation))}


def test_translates_only_foreign_and_is_idempotent(engine):
    calls = []
    with deepl(calls) as c:
        first = job.run_translation(engine, api_key="k:fx", client=c)
        second = job.run_translation(engine, api_key="k:fx", client=c)
    assert first == {"status": "success", "translated": 2, "chars": len("AI newsShort summaryChips")}
    assert second["translated"] == 0 and len(calls) == 1
    assert calls[0] == ["AI news", "Short summary", "Chips"]  # empty summary is not sent
    assert rows(engine) == {"KO:AI news": "KO:Short summary", "KO:Chips": ""}


def test_summary_arriving_later_is_translated_again(engine):
    calls = []
    with deepl(calls) as c:
        job.run_translation(engine, api_key="k:fx", client=c)
        with Session(engine) as db:
            store_news(db, [NewsItem(id="b2", title="Chips", url="https://bbc.example/2", source="BBC News",
                                     summary="Now with summary", observed_at="2026-11-23T00:00:00Z")])
            db.commit()
        result = job.run_translation(engine, api_key="k:fx", client=c)
    assert result["translated"] == 1
    assert rows(engine)["KO:Chips"] == "KO:Now with summary"


def test_missing_key_and_quota_error_write_nothing(engine):
    assert job.run_translation(engine, api_key="")["status"] == "skipped"
    with httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(456))) as c:
        result = job.run_translation(engine, api_key="k:fx", client=c)
    assert (result["status"], result["error_code"]) == ("failed", "quota_exceeded")
    assert rows(engine) == {}


def test_run_scheduled_outcomes(engine):
    with pytest.raises(job.TranslationSkipped):
        job.run_scheduled(engine_factory=lambda: engine,
                          execute=lambda e, api_key: {"status": "skipped", "error_code": "missing_api_key"})
    with pytest.raises(RuntimeError, match="quota_exceeded"):
        job.run_scheduled(engine_factory=lambda: engine,
                          execute=lambda e, api_key: {"status": "failed", "error_code": "quota_exceeded"})


def test_invalid_limit(engine):
    with pytest.raises(ValueError):
        job.run_translation(engine, api_key="k:fx", limit=26)
