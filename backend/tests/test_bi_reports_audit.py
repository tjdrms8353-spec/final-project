"""Reports (weekly/monthly) and audit trail API tests."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.features.bi.router import bi_db
from app.main import app

SAMPLE = Path(__file__).resolve().parents[2] / "frontend/public/samples/semiconductor_erp_sample.csv"


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine, tables=[t for name, t in Base.metadata.tables.items() if name.startswith("bi_")])
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


@pytest.fixture
def workspace(client):
    owner = signup(client, "owner@example.com", "대표")
    approver = signup(client, "approver@example.com", "재무팀장")
    outsider = signup(client, "outsider@example.com")
    company = client.post("/api/bi/companies", headers=owner, json={
        "name": "리본반도체", "industry": "semiconductor", "main_products": ["DDR5"],
        "interest_industries": ["AI 서버"], "trade_countries": ["미국"]}).json()
    cid = company["id"]
    client.put(f"/api/bi/companies/{cid}/members", headers=owner,
               json={"email": "approver@example.com", "role": "APPROVER"})
    up = client.post(f"/api/bi/companies/{cid}/erp/upload", headers=owner,
                     files={"file": ("sample.csv", SAMPLE.read_bytes(), "text/csv")})
    assert up.status_code == 201, up.text
    run = client.post(f"/api/bi/companies/{cid}/analyses", headers=owner).json()
    finding = next(f for f in run["findings"] if "재고" in f["title"])
    client.post(f"/api/bi/companies/{cid}/findings/{finding['id']}/decisions", headers=approver, json={
        "status": "APPROVED", "reason": "재고일수 초과", "follow_up": "생산 감산 검토"})
    return {"owner": owner, "approver": approver, "outsider": outsider, "cid": cid, "run": run}


def test_monthly_report_contains_kpis_analysis_decisions(client, workspace):
    cid = workspace["cid"]
    r = client.get(f"/api/bi/companies/{cid}/reports?kind=monthly&month={date.today().strftime('%Y-%m')}",
                   headers=workspace["owner"])
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["kind"] == "monthly" and report["company"]["name"] == "리본반도체"
    assert report["generated_by"] == "대표"
    assert any(k["code"] == "sales" and k["value"] for k in report["kpis"])
    # KPI는 보고서 월 또는 그 이전의 가장 최근 ERP 월 기준
    assert report["kpi_period"] and report["monthly_rows"][-1]["period"] == report["kpi_period"]
    assert report["analysis"] and report["analysis"][0]["findings"]
    assert any(d["status"] == "APPROVED" and "재고" in d["finding_title"] for d in report["decisions"])
    assert report["uploads"] and report["uploads"][0]["row_count"] == 48


def test_weekly_report_aggregates_period(client, workspace):
    cid = workspace["cid"]
    today = date.today().isoformat()
    r = client.get(f"/api/bi/companies/{cid}/reports?kind=weekly&anchor={today}", headers=workspace["owner"])
    assert r.status_code == 200, r.text
    report = r.json()
    assert report["kind"] == "weekly" and report["kpi_period"]
    assert "summary" in report and "record_count" in report["summary"]["weekly"]


def test_report_period_validation_and_access(client, workspace):
    cid = workspace["cid"]
    assert client.get(f"/api/bi/companies/{cid}/reports?kind=monthly&month=2026-13",
                      headers=workspace["owner"]).status_code == 422
    assert client.get(f"/api/bi/companies/{cid}/reports", headers=workspace["outsider"]).status_code == 404
    # viewer/analyst 등 모든 구성원은 보고서를 읽을 수 있다
    client.put(f"/api/bi/companies/{cid}/members", headers=workspace["owner"],
               json={"email": "outsider@example.com", "role": "VIEWER"})
    assert client.get(f"/api/bi/companies/{cid}/reports", headers=workspace["outsider"]).status_code == 200


def test_audit_log_records_events_and_filters(client, workspace):
    cid = workspace["cid"]
    client.post(f"/api/bi/companies/{cid}/simulate", headers=workspace["owner"], json={"fx_pct": 5})
    client.get(f"/api/bi/companies/{cid}/reports?kind=monthly", headers=workspace["owner"])

    r = client.get(f"/api/bi/companies/{cid}/audit-logs?limit=100", headers=workspace["owner"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["total"] >= 6
    actions = [i["action"] for i in body["items"]]
    for expected in ("COMPANY_CREATED", "MEMBER_UPDATED", "ERP_UPLOAD", "ANALYSIS_RUN", "DECISION",
                     "SIMULATION_RUN", "REPORT_GENERATED"):
        assert expected in actions, expected
    first = body["items"][0]
    assert first["user"] == "대표" and first["action"] == "REPORT_GENERATED"
    assert first["detail"]["kind"] == "monthly"

    filtered = client.get(f"/api/bi/companies/{cid}/audit-logs?action=DECISION", headers=workspace["owner"]).json()
    assert filtered["total"] == 1 and filtered["items"][0]["action"] == "DECISION"
    assert filtered["items"][0]["detail"]["status"] == "APPROVED"

    assert client.get(f"/api/bi/companies/{cid}/audit-logs", headers=workspace["outsider"]).status_code == 404
