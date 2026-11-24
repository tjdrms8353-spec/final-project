"""Tests for the auto_parts industry, FX-sensitivity scenario, macro indicators, company update."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.features.bi import market
from app.features.bi.router import bi_db
from app.features.trends.models import NewsArticle, NewsTranslation
from app.main import app

SAMPLE = Path(__file__).resolve().parents[2] / "frontend/public/samples/semiconductor_erp_sample.csv"


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[t for name, t in Base.metadata.tables.items() if name.startswith("bi_")]
                             + [NewsArticle.__table__, NewsTranslation.__table__])
    yield engine
    engine.dispose()


@pytest.fixture
def client(engine):
    def override():
        with Session(engine) as db:
            yield db
    app.dependency_overrides[bi_db] = override
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(bi_db, None)


def signup(client, email, name="사용자"):
    r = client.post("/api/bi/auth/register", json={"email": email, "name": name, "password": "password123"})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_auto_parts_template_and_company_update(client, engine):
    industries = client.get("/api/bi/industries").json()
    auto = next(i for i in industries if i["code"] == "auto_parts")
    assert "자동차 부품" in auto["label"]
    assert "US_10Y_YIELD" in auto["market_indicators"] and "WTI_OIL" in auto["market_indicators"]
    assert any(k["code"] == "fx_purchase_share_pct" for k in auto["kpis"])

    owner = signup(client, "owner@example.com", "대표")
    created = client.post("/api/bi/companies", headers=owner, json={
        "name": "한라모터스 부품", "industry": "auto_parts", "main_products": ["브레이크 캘리퍼"],
        "annual_import_krw": 5000000000}).json()
    cid = created["id"]
    assert created["industry_label"] == "자동차 부품 제조" and created["annual_import_krw"] == 5000000000

    analyst = signup(client, "analyst@example.com", "분석가")
    client.put(f"/api/bi/companies/{cid}/members", headers=owner, json={"email": "analyst@example.com", "role": "ANALYST"})
    assert client.put(f"/api/bi/companies/{cid}", headers={**analyst}, json={
        "name": "한라모터스", "industry": "auto_parts", "annual_import_krw": 4000000000}).status_code == 403
    updated = client.put(f"/api/bi/companies/{cid}", headers=owner, json={
        "name": "한라모터스", "industry": "auto_parts", "annual_import_krw": 4000000000}).json()
    assert updated["annual_import_krw"] == 4000000000
    logs = client.get(f"/api/bi/companies/{cid}/audit-logs?action=COMPANY_UPDATED", headers=owner).json()
    assert logs["total"] == 1


def test_fx_sensitivity_scenario_finding(client, engine):
    today = date.today()
    with Session(engine) as db:
        market.store_indicators(db, [
            {"code": "USD/KRW", "obs_date": today - timedelta(days=40), "value": 1360.0, "source": "test", "source_url": "https://example.com/fx"},
            {"code": "USD/KRW", "obs_date": today, "value": 1403.52, "source": "test", "source_url": "https://example.com/fx"}])
        db.commit()
    owner = signup(client, "owner@example.com", "대표")
    company = client.post("/api/bi/companies", headers=owner, json={
        "name": "한라모터스 부품", "industry": "auto_parts", "main_products": ["브레이크 캘리퍼"],
        "annual_import_krw": 5000000000}).json()
    cid = company["id"]
    client.post(f"/api/bi/companies/{cid}/erp/upload", headers=owner,
                files={"file": ("sample.csv", SAMPLE.read_bytes(), "text/csv")})
    run = client.post(f"/api/bi/companies/{cid}/analyses", headers=owner).json()
    scenario = next((f for f in run["findings"] if "시나리오" in f["title"]), None)
    assert scenario is not None, [f["title"] for f in run["findings"]]
    assert scenario["kind"] == "risk" and "3.2" in scenario["title"]
    impact = next(x for x in scenario["facts"] if x["label"].startswith("환율 변동 단순 적용"))
    assert impact["value"] == pytest.approx(160000000, rel=1e-6)


def test_macro_fetch_and_collect(client, engine):
    payload = {"chart": {"result": [{"timestamp": [1700000000, 1700086400],
                                     "indicators": {"quote": [{"close": [4.25, None]}]}}]}}

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    macro_client = httpx.Client(transport=httpx.MockTransport(handler))
    rows = market.fetch_macro(["US_10Y_YIELD", "WTI_OIL"], days=30, client=macro_client)
    assert len(rows) == 2 and all(r["code"] in {"US_10Y_YIELD", "WTI_OIL"} for r in rows)
    with Session(engine) as db:
        result = market.collect_macro(db, days=30, client=macro_client)
        db.commit()
    assert result["fetched"] == 2
    with Session(engine) as db:
        series = market.indicator_series(db, "US_10Y_YIELD")
        assert [s.value for s in series] == [4.25]

def test_macro_endpoint(monkeypatch, client):
    monkeypatch.setattr(market, "collect_macro", lambda db, days=180, client=None: {"fetched": 1, "inserted": 1})
    owner = signup(client, "owner@example.com")
    r = client.post("/api/bi/market/macro/collect", headers=owner)
    assert r.status_code == 200 and r.json() == {"fetched": 1, "inserted": 1}
