"""정식 전환 B — 외부 데이터 수집 어댑터·수집 서비스 테스트.

실제 네트워크 호출은 하지 않는다 — base.get_json/get_text와
수집기 목록을 monkeypatch로 교체해 검증한다.
"""
from datetime import datetime

import pytest

from app.database import SessionLocal
from app.models import AuditLog, Company, MarketSeries, NewsItem
from app.services import collection_service
from app.services.collectors.base import CollectorResult
from app.services.collectors import fx_ecos, news_stub
from app.services.collectors.fx_ecos import EcosRateCollector, EximFxCollector
from app.services.collectors.news_stub import NewsCollector, parse_rss


# ---------- EXIM 환율 ----------

EXIM_SAMPLE = [
    {"cur_unit": "USD", "deal_bas_r": "1,385.20"},
    {"cur_unit": "JPY(100)", "deal_bas_r": "912.34"},
    {"cur_unit": "EUR", "deal_bas_r": "1,512.05"},
    {"cur_unit": "GBP", "deal_bas_r": "1,800.00"},   # 매핑 대상 아님 → 제외
]


def test_exim_collect_maps_currencies(monkeypatch):
    monkeypatch.setattr(fx_ecos, "EXIM_API_KEY", "key")
    monkeypatch.setattr(fx_ecos, "get_json",
                        lambda url, params=None: EXIM_SAMPLE)
    res = EximFxCollector().collect()
    keys = {s["series_key"] for s in res.series}
    assert keys == {"USD_KRW", "JPY_KRW", "EUR_KRW"}
    usd = next(s for s in res.series if s["series_key"] == "USD_KRW")
    assert usd["value"] == 1385.20
    assert usd["unit"] == "KRW"
    assert usd["month"] == datetime.utcnow().strftime("%Y-%m")
    assert res.source == "한국수출입은행 EXIM"
    assert not res.errors


def test_exim_disabled_without_key(monkeypatch):
    monkeypatch.setattr(fx_ecos, "EXIM_API_KEY", "")
    c = EximFxCollector()
    assert not c.enabled
    res = c.collect()
    assert res.series == [] and res.errors


# ---------- ECOS 기준금리 ----------

ECOS_SAMPLE = {"StatisticSearch": {"list_total_count": 2, "row": [
    {"TIME": "202410", "DATA_VALUE": "3.25"},
    {"TIME": "202411", "DATA_VALUE": "3.00"},
]}}


def test_ecos_collect_maps_base_rate(monkeypatch):
    monkeypatch.setattr(fx_ecos, "ECOS_API_KEY", "key")
    monkeypatch.setattr(fx_ecos, "get_json",
                        lambda url, params=None: ECOS_SAMPLE)
    res = EcosRateCollector().collect()
    assert len(res.series) == 2
    r = res.series[0]
    assert r["series_key"] == "BASE_RATE" and r["unit"] == "%"
    assert r["month"] == "2024-10" and r["value"] == 3.25


def test_ecos_disabled_without_key(monkeypatch):
    monkeypatch.setattr(fx_ecos, "ECOS_API_KEY", "")
    assert not EcosRateCollector().enabled


# ---------- RSS 뉴스 ----------

RSS_SAMPLE = """<?xml version="1.0"?>
<rss version="2.0"><channel><title>feed</title>
<item>
  <title>원달러 환율 급등에 수출입 기업 긴장</title>
  <link>https://news.example.com/1</link>
  <pubDate>Tue, 24 Nov 2026 09:00:00 GMT</pubDate>
  <description>&lt;b&gt;원달러&lt;/b&gt; 환율이 급등하면서 수입 원자재 부담이 커졌다.</description>
  <source>테스트경제</source>
</item>
<item>
  <title>철강 원자재 가격 상승세</title>
  <link>https://news.example.com/2</link>
  <pubDate>Tue, 24 Nov 2026 08:00:00 GMT</pubDate>
  <description>철강·구리 가격이 상승했다.</description>
</item>
</channel></rss>"""


def test_rss_parse_items():
    items = parse_rss(RSS_SAMPLE, "example.com")
    assert len(items) == 2
    a, b = items
    assert a["title"].startswith("원달러")
    assert a["link"] == "https://news.example.com/1"
    assert a["source"] == "테스트경제"
    assert "<b>" not in a["summary"]            # HTML 태그 제거
    assert a["published_at"].year == 2026
    assert b["source"] == "example.com"         # source 태그 없으면 피드 도메인


def test_news_collector_disabled_flag(monkeypatch):
    monkeypatch.setattr(news_stub, "NEWS_COLLECT_ENABLED", False)
    assert not NewsCollector().enabled


def test_news_collector_collect(monkeypatch):
    monkeypatch.setattr(news_stub, "NEWS_COLLECT_ENABLED", True)
    monkeypatch.setattr(news_stub, "NEWS_RSS_URLS", "https://feed.example/rss")
    monkeypatch.setattr(news_stub, "get_text",
                        lambda url, params=None: RSS_SAMPLE)
    res = NewsCollector().collect()
    assert len(res.news) == 2 and not res.errors


# ---------- 수집 서비스 (저장·중복·격리) ----------

class FakeCollector:
    name = "fake"
    source = "테스트 수집기"

    @property
    def enabled(self):
        return True

    def collect(self):
        return CollectorResult(
            source=self.source,
            series=[{"series_key": "TEST_RATE", "series_name": "테스트지표",
                     "unit": "%", "month": "2099-01", "value": 1.5}],
            news=[{"title": "테스트 수집 뉴스", "summary": "요약",
                   "source": "테스트뉴스", "link": "https://t.example/1",
                   "published_at": datetime(2026, 11, 24)}],
        )


def _run(db, cid):
    return collection_service.run_collection(db, company_id=cid)


@pytest.fixture()
def fake_collectors(monkeypatch):
    monkeypatch.setattr(collection_service, "ALL_COLLECTORS", [FakeCollector])


def test_run_collection_saves_per_company(client, fake_collectors):
    db = SessionLocal()
    try:
        cid = db.query(Company.id).first()[0]
        out = _run(db, cid)
        assert out["collectors"][0]["series"] == 1
        assert out["collectors"][0]["news"] == 1

        s = db.query(MarketSeries).filter_by(
            company_id=cid, series_key="TEST_RATE", month="2099-01").one()
        assert s.value == 1.5 and s.source == "테스트 수집기"

        n = db.query(NewsItem).filter_by(
            company_id=cid, link="https://t.example/1").one()
        assert n.is_demo is False and n.source == "테스트뉴스"

        # 감사 로그 기록
        assert db.query(AuditLog).filter_by(action="collection.run").count() >= 1
    finally:
        db.close()


def test_run_collection_dedup_on_rerun(client, fake_collectors):
    db = SessionLocal()
    try:
        cid = db.query(Company.id).first()[0]
        _run(db, cid)
        _run(db, cid)   # 재실행
        assert db.query(MarketSeries).filter_by(
            company_id=cid, series_key="TEST_RATE").count() == 1
        assert db.query(NewsItem).filter_by(
            company_id=cid, link="https://t.example/1").count() == 1
    finally:
        db.close()


def test_run_collection_company_isolation(client, fake_collectors):
    db = SessionLocal()
    try:
        cid = db.query(Company.id).first()[0]
        other = Company(name="격리기업")
        db.add(other)
        db.commit()
        _run(db, cid)
        assert db.query(MarketSeries).filter_by(
            company_id=other.id, series_key="TEST_RATE").count() == 0
    finally:
        db.close()


# ---------- 수집 API ----------

def test_collection_status_api(client, owner_headers):
    r = client.get("/api/collection/status", headers=owner_headers)
    assert r.status_code == 200
    data = r.json()
    names = {c["name"] for c in data["collectors"]}
    assert names == {"exim_fx", "ecos_rate", "news_rss"}
    # 테스트 환경: 키 미설정·RSS 비활성 → 모두 enabled False
    assert all(not c["enabled"] for c in data["collectors"])


def test_collection_run_requires_admin(client, viewer_headers, owner_headers):
    r = client.post("/api/collection/run", headers=viewer_headers)
    assert r.status_code == 403
    r = client.post("/api/collection/run", headers=owner_headers)
    assert r.status_code == 200
    assert "collectors" in r.json()


def test_collection_run_requires_auth(client):
    assert client.post("/api/collection/run").status_code == 401
    assert client.get("/api/collection/status").status_code == 401
