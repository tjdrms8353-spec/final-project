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
from app.features.trends.repository import store_news
from app.features.trends.schemas import NewsItem
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
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()["user"]


def seed_market_and_news(engine):
    today = date.today()
    with Session(engine) as db:
        market.store_indicators(db, [
            {"code": "USD/KRW", "obs_date": today - timedelta(days=d), "value": v, "source": "test", "source_url": "https://example.com/fx"}
            for d, v in ((40, 1350.0), (30, 1360.0), (0, 1420.0))])
        db.commit()
    now = datetime.now(timezone.utc)
    with Session(engine) as db, db.begin():
        store_news(db, [NewsItem(id=f"n{i}", title=f"HBM 반도체 수요 기사 {i}", source="연합뉴스",
                                 url=f"https://example.com/news/{i}", observed_at=now - timedelta(days=1)) for i in range(4)])


def test_full_flow_company_upload_dashboard_analysis_decision(client, engine):
    seed_market_and_news(engine)
    owner, _ = signup(client, "owner@example.com", "대표")
    analyst, analyst_user = signup(client, "analyst@example.com", "분석가")
    outsider, _ = signup(client, "other@example.com")

    company = client.post("/api/bi/companies", headers=owner, json={
        "name": "리본반도체", "industry": "semiconductor", "main_products": ["DDR5", "HBM"],
        "interest_industries": ["AI 서버"], "trade_countries": ["미국", "일본", "대만"]}).json()
    cid = company["id"]
    assert company["role"] == "OWNER" and "USD/KRW" in company["interest_indicators"]
    assert client.get(f"/api/bi/companies/{cid}", headers=outsider).status_code == 404
    assert client.put(f"/api/bi/companies/{cid}/members", headers=owner,
                      json={"email": "analyst@example.com", "role": "ANALYST"}).status_code == 200

    up = client.post(f"/api/bi/companies/{cid}/erp/upload", headers=analyst,
                     files={"file": ("sample.csv", SAMPLE.read_bytes(), "text/csv")})
    assert up.status_code == 201, up.text
    assert up.json()["accepted"] == 48 and up.json()["rejected"] == 0

    dash = client.get(f"/api/bi/companies/{cid}/dashboard", headers=analyst).json()
    assert dash["period"] == "2026-10" and len(dash["monthly"]) == 6
    kpi = {k["code"]: k for k in dash["kpis"]}
    assert kpi["sales"]["value"] == 1_150_000_000
    assert kpi["export_share_pct"]["value"] == 80.0
    assert dash["news"]["recent_count"] == 4
    assert dash["indicators"]["USD/KRW"]["change_30d"]["change_pct"] == 4.41

    analysis = client.post(f"/api/bi/companies/{cid}/analyses", headers=analyst)
    assert analysis.status_code == 201, analysis.text
    data = analysis.json()
    assert data["narrative_source"] == "template"
    titles = [f["title"] for f in data["findings"]]
    kinds = {f["kind"] for f in data["findings"]}
    assert {"risk", "opportunity", "change"} <= kinds
    assert any("매출 전월 대비" in t for t in titles)
    assert any("재고 보유일수" in t for t in titles)
    risk = next(f for f in data["findings"] if "매출 전월 대비" in f["title"])
    assert risk["facts"][2]["value"] == -12.21
    assert any(e["type"] == "news" for e in risk["evidence"])
    assert "규칙 기반 추론" in risk["inference"]

    decision_body = {"status": "APPROVED", "reason": "거래처 점검 필요", "assignee_id": analyst_user["id"],
                     "follow_up": "상위 3개 거래처 수주 점검", "due_date": "2026-12-15"}
    url = f"/api/bi/companies/{cid}/findings/{risk['id']}/decisions"
    assert client.post(url, headers=analyst, json=decision_body).status_code == 403
    assert client.post(url, headers=outsider, json=decision_body).status_code == 404
    decided = client.post(url, headers=owner, json=decision_body)
    assert decided.status_code == 201 and decided.json()["finding_status"] == "APPROVED"

    history = client.get(f"/api/bi/companies/{cid}/decisions", headers=analyst).json()
    assert history[0]["status"] == "APPROVED" and history[0]["assignee"] == "분석가"
    actions = client.get(f"/api/bi/companies/{cid}/actions", headers=analyst).json()
    assert actions[0]["title"] == "상위 3개 거래처 수주 점검"
    patched = client.patch(f"/api/bi/companies/{cid}/actions/{actions[0]['id']}", headers=analyst, json={"status": "DONE"})
    assert patched.json()["status"] == "DONE"
    stored = client.get(f"/api/bi/companies/{cid}/analyses/{data['id']}", headers=analyst).json()
    assert next(f for f in stored["findings"] if f["id"] == risk["id"])["status"] == "APPROVED"

    sim = client.post(f"/api/bi/companies/{cid}/simulate", headers=analyst,
                      json={"fx_pct": 5, "purchase_price_pct": 10, "sales_pct": -8, "volume_pct": 15}).json()
    assert sim["before"]["profit"] == 1_150_000_000 - 640_000_000 - 205_000_000
    assert sim["after"]["sales"] == round((1_150_000_000 + 920_000_000 * 0.05) * 0.92 * 1.15, 2)


def test_auth_and_upload_validation(client):
    assert client.get("/api/bi/companies").status_code == 401
    assert client.get("/api/bi/companies", headers={"Authorization": "Bearer bad.token"}).status_code == 401
    owner, _ = signup(client, "a@example.com")
    assert client.post("/api/bi/auth/register", json={"email": "a@example.com", "name": "x", "password": "password123"}).status_code == 409
    assert client.post("/api/bi/auth/login", json={"email": "a@example.com", "password": "wrong"}).status_code == 401
    cid = client.post("/api/bi/companies", headers=owner, json={"name": "A"}).json()["id"]
    assert client.post(f"/api/bi/companies/{cid}/analyses", headers=owner).status_code == 422
    bad = client.post(f"/api/bi/companies/{cid}/erp/upload", headers=owner, files={"file": ("x.txt", b"a", "text/plain")})
    assert bad.status_code == 422
    korean = "일자,구분,품목,금액\n2026-10-01,매출,칩,\"1,000\"\n2026-10-02,기타,칩,10\n".encode("cp949")
    ok = client.post(f"/api/bi/companies/{cid}/erp/upload", headers=owner, files={"file": ("k.csv", korean, "text/csv")}).json()
    assert ok["accepted"] == 1 and ok["rejected"] == 1 and "3행" in ok["errors"][0]
    assert client.get("/api/bi/erp/template.csv").text.startswith("date,category")


def test_fx_collect_uses_frankfurter_response(client, engine):
    owner, _ = signup(client, "fx@example.com")
    payload = {"rates": {"2026-11-20": {"KRW": 1400.5}, "2026-11-21": {"KRW": 1402.0}}}
    transport = httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
    with Session(engine) as db:
        result = market.collect_fx(db, ["USD/KRW"], client=httpx.Client(transport=transport))
        db.commit()
    assert result == {"fetched": 2, "inserted": 2}
    series = client.get("/api/bi/market/indicators", headers=owner, params={"code": "USD/KRW"}).json()
    assert [s["value"] for s in series["series"]] == [1400.5, 1402.0]
