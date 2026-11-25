"""정식 전환 B 보완 — 수집 어댑터·공통 저장 구조·스케줄 테스트.

실제 네트워크 호출은 하지 않는다 — base.get_json/get_text와
수집기 목록을 monkeypatch로 교체해 검증한다.
"""
from datetime import datetime

import pytest

from app.database import SessionLocal
from app.models import (
    AuditLog, CollectionRun, CollectorState, Company, CompanyNewsScore,
    MarketSeries, NewsItem,
)
from app.services import collection_service
from app.services import collectors as collectors_pkg
from app.services.collectors import collector_active
from app.services.collectors.base import CollectorResult
from app.services.collectors import fx_ecos, global_sources, news_stub
from app.services.collectors.fx_ecos import EcosRateCollector, EximFxCollector
from app.services.collectors.global_sources import (
    DartDisclosureCollector, EiaSeriesCollector, FredSeriesCollector,
    GdeltNewsCollector,
)
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


# ---------- GDELT ----------

GDELT_SAMPLE = {"articles": [
    {"url": "https://g.example/1", "title": "반도체 수출 회복세",
     "domain": "g.example", "seendate": "20261124T120000Z"},
    {"url": "https://g.example/2", "title": "금리 동결 전망",
     "domain": "g.example", "seendate": "bad-date"},
]}


def test_gdelt_collect_maps_articles(monkeypatch):
    monkeypatch.setattr(global_sources, "GDELT_ENABLED", True)
    monkeypatch.setattr(global_sources, "get_json",
                        lambda url, params=None: GDELT_SAMPLE)
    res = GdeltNewsCollector().collect()
    assert len(res.news) == 2 and not res.errors
    a = res.news[0]
    assert a["link"] == "https://g.example/1"
    assert a["source"] == "g.example"
    assert a["published_at"] == datetime(2026, 11, 24, 12, 0, 0)
    assert res.news[1]["published_at"]  # 파싱 실패 시 현재 시각 폴백


def test_gdelt_disabled_flag(monkeypatch):
    monkeypatch.setattr(global_sources, "GDELT_ENABLED", False)
    assert not GdeltNewsCollector().enabled


# ---------- FRED / EIA / DART (키 게이트) ----------

FRED_SAMPLE = {"observations": [
    {"date": "2026-10-01", "value": "1385.2"},
    {"date": "2026-11-01", "value": "."},          # 결측 → 건너뜀
    {"date": "2026-09-01", "value": "1390.0"},
]}


def test_fred_collect_maps_series(monkeypatch):
    monkeypatch.setattr(global_sources, "FRED_API_KEY", "key")
    monkeypatch.setattr(global_sources, "get_json",
                        lambda url, params=None: FRED_SAMPLE)
    res = FredSeriesCollector().collect()
    # 3개 시리즈 × 유효 2건 = 6건 (같은 mock 응답을 모든 시리즈가 공유)
    assert len(res.series) == 6
    keys = {s["series_key"] for s in res.series}
    assert keys == {"USD_KRW", "FED_RATE", "WTI_OIL"}
    assert all(s["month"] in ("2026-10", "2026-09") for s in res.series)


def test_fred_disabled_without_key(monkeypatch):
    monkeypatch.setattr(global_sources, "FRED_API_KEY", "")
    c = FredSeriesCollector()
    assert not c.enabled
    assert c.collect().errors


EIA_SAMPLE = {"response": {"data": [
    {"period": "2026-10", "value": "72.5", "series": "RWTC"},
    {"period": "2026-09", "value": None},          # 결측 → 건너뜀
]}}


def test_eia_collect_maps_series(monkeypatch):
    monkeypatch.setattr(global_sources, "EIA_API_KEY", "key")
    monkeypatch.setattr(global_sources, "get_json",
                        lambda url, params=None: EIA_SAMPLE)
    res = EiaSeriesCollector().collect()
    assert len(res.series) == 1
    s = res.series[0]
    assert s["series_key"] == "WTI_OIL" and s["month"] == "2026-10"
    assert s["value"] == 72.5


def test_eia_disabled_without_key(monkeypatch):
    monkeypatch.setattr(global_sources, "EIA_API_KEY", "")
    assert not EiaSeriesCollector().enabled


DART_SAMPLE = {"list": [
    {"corp_name": "테스트전자", "report_nm": "분기보고서",
     "rcept_dt": "20261120", "rcept_no": "20261120000123", "flr_nm": "테스트전자"},
]}


def test_dart_collect_maps_disclosures(monkeypatch):
    monkeypatch.setattr(global_sources, "DART_API_KEY", "key")
    monkeypatch.setattr(global_sources, "DART_CORP_CODES", "00126380")
    monkeypatch.setattr(global_sources, "get_json",
                        lambda url, params=None: DART_SAMPLE)
    res = DartDisclosureCollector().collect()
    assert len(res.news) == 1 and not res.errors
    n = res.news[0]
    assert "[공시] 테스트전자" in n["title"]
    assert "20261120000123" in n["link"]
    assert n["published_at"] == datetime(2026, 11, 20)


def test_dart_disabled_without_key_or_codes(monkeypatch):
    monkeypatch.setattr(global_sources, "DART_API_KEY", "")
    monkeypatch.setattr(global_sources, "DART_CORP_CODES", "00126380")
    assert not DartDisclosureCollector().enabled
    monkeypatch.setattr(global_sources, "DART_API_KEY", "key")
    monkeypatch.setattr(global_sources, "DART_CORP_CODES", "")
    assert not DartDisclosureCollector().enabled


# ---------- 이용 조건 게이팅 ----------

def test_license_gate_blocks_unverified_in_prod(monkeypatch):
    monkeypatch.setattr(collectors_pkg, "IS_PROD", True)
    monkeypatch.setattr(collectors_pkg, "ALLOW_UNVERIFIED_SOURCES", False)
    monkeypatch.setattr(news_stub, "NEWS_COLLECT_ENABLED", True)
    # Google 뉴스 RSS는 license_verified=False → 운영에서 차단
    assert not collector_active(NewsCollector())
    # 검증된 공급처(GDELT)는 허용
    monkeypatch.setattr(global_sources, "GDELT_ENABLED", True)
    assert collector_active(GdeltNewsCollector())


def test_license_gate_override(monkeypatch):
    monkeypatch.setattr(collectors_pkg, "IS_PROD", True)
    monkeypatch.setattr(collectors_pkg, "ALLOW_UNVERIFIED_SOURCES", True)
    monkeypatch.setattr(news_stub, "NEWS_COLLECT_ENABLED", True)
    assert collector_active(NewsCollector())


def test_license_gate_dev_allows_all(monkeypatch):
    monkeypatch.setattr(collectors_pkg, "IS_PROD", False)
    monkeypatch.setattr(news_stub, "NEWS_COLLECT_ENABLED", True)
    assert collector_active(NewsCollector())


# ---------- 수집 서비스 (공통 저장·점수·이력) ----------

class FakeCollector:
    name = "fake"
    source = "테스트 수집기"
    license_verified = True

    @property
    def enabled(self):
        return True

    def collect(self):
        return CollectorResult(
            source=self.source,
            series=[{"series_key": "TEST_RATE", "series_name": "테스트지표",
                     "unit": "%", "month": "2099-01", "value": 1.5}],
            news=[{"title": "테스트 수집 뉴스 반도체", "summary": "요약",
                   "source": "테스트뉴스", "link": "https://t.example/1",
                   "published_at": datetime(2026, 11, 24)}],
        )


def _run(db, cid=None):
    return collection_service.run_collection(db, company_id=cid)


@pytest.fixture()
def fake_collectors(monkeypatch):
    monkeypatch.setattr(collection_service, "ALL_COLLECTORS", [FakeCollector])


def _first_company(db):
    return db.query(Company).first()


def test_run_collection_saves_common_data(client, fake_collectors):
    """공통 데이터는 company_id=NULL로 한 번 저장, 기업 점수만 별도."""
    db = SessionLocal()
    try:
        company = _first_company(db)
        out = _run(db, cid=company.id)
        assert out["collectors"][0]["series"] == 1
        assert out["collectors"][0]["news"] == 1

        s = db.query(MarketSeries).filter_by(
            company_id=None, series_key="TEST_RATE", month="2099-01").one()
        assert s.value == 1.5 and s.source == "테스트 수집기"

        n = db.query(NewsItem).filter_by(
            company_id=None, link="https://t.example/1").one()
        assert n.is_demo is False and n.source == "테스트뉴스"

        score = db.query(CompanyNewsScore).filter_by(
            company_id=company.id, news_item_id=n.id).one()
        assert score.relevance_score > 0

        assert db.query(AuditLog).filter_by(action="collection.run").count() >= 1
    finally:
        db.close()


def test_run_collection_dedup_on_rerun(client, fake_collectors):
    """재수집 시 공통 행·기업 점수 모두 중복 생성되지 않는다."""
    db = SessionLocal()
    try:
        company = _first_company(db)
        _run(db, cid=company.id)
        _run(db, cid=company.id)
        assert db.query(MarketSeries).filter_by(
            company_id=None, series_key="TEST_RATE").count() == 1
        n = db.query(NewsItem).filter_by(
            company_id=None, link="https://t.example/1").one()
        assert db.query(CompanyNewsScore).filter_by(
            company_id=company.id, news_item_id=n.id).count() == 1
    finally:
        db.close()


def test_shared_news_two_companies_no_duplication(client, fake_collectors):
    """기업 2개 이상이 동일 뉴스를 공유하고 점수는 독립적으로 저장된다."""
    db = SessionLocal()
    try:
        company = _first_company(db)
        other = Company(name="격리기업B", industry="반도체",
                        products="메모리")
        db.add(other)
        db.commit()

        _run(db)   # 전체 기업 대상 수집
        n = db.query(NewsItem).filter_by(
            company_id=None, link="https://t.example/1").one()

        # 뉴스 원본은 1건만 존재
        assert db.query(NewsItem).filter_by(
            link="https://t.example/1").count() == 1
        # 두 기업 모두 점수 보유 — 서로 다른 행
        s_a = db.query(CompanyNewsScore).filter_by(
            company_id=company.id, news_item_id=n.id).one()
        s_b = db.query(CompanyNewsScore).filter_by(
            company_id=other.id, news_item_id=n.id).one()
        assert s_a.id != s_b.id
    finally:
        db.close()


def test_score_independence_between_companies(client, fake_collectors):
    """키워드가 다른 기업은 다른 관련성 점수를 가진다."""
    db = SessionLocal()
    try:
        matched = Company(name="매칭기업", industry="반도체",
                          products="반도체")
        unmatched = Company(name="비매칭기업", industry="식품",
                            products="과자")
        db.add_all([matched, unmatched])
        db.commit()

        _run(db)   # 전체 기업 점수 생성 (공통 뉴스 포함)
        n = db.query(NewsItem).filter_by(
            company_id=None, link="https://t.example/1").one()
        s_hi = db.query(CompanyNewsScore).filter_by(
            company_id=matched.id, news_item_id=n.id).one()
        s_lo = db.query(CompanyNewsScore).filter_by(
            company_id=unmatched.id, news_item_id=n.id).one()
        # '반도체' 키워드 매칭 기업의 점수가 더 높다
        assert s_hi.relevance_score > s_lo.relevance_score
    finally:
        db.close()


def test_collector_state_and_run_history(client, fake_collectors):
    """수집 실행이 collector_states와 collection_runs에 기록된다."""
    db = SessionLocal()
    try:
        _run(db)
        st = db.get(CollectorState, "fake")
        assert st is not None and st.last_run_at is not None
        assert st.next_run_at is not None
        run = db.query(CollectionRun).filter_by(collector="fake").first()
        assert run is not None and run.status == "ok"
        assert run.series_count == 1
    finally:
        db.close()


def test_due_collectors_respects_interval(client, fake_collectors):
    """직전 수집 후 주기가 지나지 않으면 due 목록에 없다."""
    db = SessionLocal()
    try:
        _run(db)
        due = collection_service.due_collectors(db)
        assert all(c.name != "fake" for c in due)
        # next_run_at을 과거로 돌리면 다시 due에 포함
        st = db.get(CollectorState, "fake")
        st.next_run_at = datetime(2020, 1, 1)
        db.commit()
        due = collection_service.due_collectors(db)
        assert any(c.name == "fake" for c in due)
    finally:
        db.close()


# ---------- 수집 API ----------

EXPECTED_COLLECTOR_NAMES = {
    "exim_fx", "ecos_rate", "news_rss", "gdelt", "fred", "eia", "dart",
}


def test_collection_status_api(client, owner_headers):
    r = client.get("/api/collection/status", headers=owner_headers)
    assert r.status_code == 200
    data = r.json()
    names = {c["name"] for c in data["collectors"]}
    assert names == EXPECTED_COLLECTOR_NAMES
    # 테스트 환경: 키 미설정·RSS/GDELT 비활성 → 모두 enabled False
    assert all(not c["enabled"] for c in data["collectors"])
    assert "recent_runs" in data and "company_data" in data


def test_collection_run_requires_admin(client, viewer_headers, owner_headers):
    collection_service._MANUAL_RUN_AT.clear()
    r = client.post("/api/collection/run", headers=viewer_headers)
    assert r.status_code == 403
    r = client.post("/api/collection/run", headers=owner_headers)
    assert r.status_code == 200
    assert "collectors" in r.json()


def test_collection_run_requires_auth(client):
    collection_service._MANUAL_RUN_AT.clear()
    assert client.post("/api/collection/run").status_code == 401
    assert client.get("/api/collection/status").status_code == 401


def test_manual_run_rate_limit(client, owner_headers):
    """기업 관리자 수동 실행은 1시간 1회로 제한된다."""
    collection_service._MANUAL_RUN_AT.clear()
    r = client.post("/api/collection/run", headers=owner_headers)
    assert r.status_code == 200
    r = client.post("/api/collection/run", headers=owner_headers)
    assert r.status_code == 429
    collection_service._MANUAL_RUN_AT.clear()


# ---------- 뉴스 API 회귀 (공통 데이터 + 기업별 점수 병합) ----------

def test_news_api_merges_common_and_scores(client, fake_collectors,
                                           owner_headers):
    """공통 뉴스가 목록에 보이고 기업별 점수가 병합된다."""
    db = SessionLocal()
    try:
        company = _first_company(db)
        _run(db, cid=company.id)
    finally:
        db.close()
    r = client.get("/api/news", headers=owner_headers)
    assert r.status_code == 200
    items = [i for i in r.json()["items"]
             if i["link"] == "https://t.example/1"]
    assert items, "공통 수집 뉴스가 목록에 없음"
    assert items[0]["relevance_score"] > 0    # 기업별 점수 병합됨
    assert items[0]["is_demo"] is False


def test_news_detail_common_access(client, fake_collectors, owner_headers):
    """공통 뉴스는 ID로 직접 조회 가능."""
    db = SessionLocal()
    try:
        company = _first_company(db)
        _run(db, cid=company.id)
        n = db.query(NewsItem).filter_by(
            company_id=None, link="https://t.example/1").one()
        news_id = n.id
    finally:
        db.close()
    r = client.get(f"/api/news/{news_id}", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["title"].startswith("테스트 수집 뉴스")
