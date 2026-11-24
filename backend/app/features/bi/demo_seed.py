"""Seed a demo company through the public API: python -m app.features.bi.demo_seed (needs DATABASE_URL)."""
from pathlib import Path

from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_engine
from app.main import app as api
import app.models  # noqa: F401,E402

DEMO_PASSWORD = "dayribbon-demo"
USERS = [
    ("owner@demo.dayribbon.kr", "김대표", "OWNER"),
    ("approver@demo.dayribbon.kr", "이재무 (재무팀장)", "APPROVER"),
    ("analyst@demo.dayribbon.kr", "박분석 (경영기획)", "ANALYST"),
    ("viewer@demo.dayribbon.kr", "최조회 (외부 감사)", "VIEWER"),
]
SAMPLE = Path(__file__).resolve().parents[4] / "frontend/public/samples/semiconductor_erp_sample.csv"


def seed(client: TestClient) -> dict:
    tokens = {}
    for email, name, _ in USERS:
        r = client.post("/api/bi/auth/register", json={"email": email, "name": name, "password": DEMO_PASSWORD})
        if r.status_code != 201 and r.status_code != 200:
            r = client.post("/api/bi/auth/login", json={"email": email, "password": DEMO_PASSWORD})
        r.raise_for_status()
        tokens[email] = {"Authorization": f"Bearer {r.json()['token']}"}
    owner = tokens[USERS[0][0]]
    if client.get("/api/bi/companies", headers=owner).json():
        return {"skipped": "already seeded"}
    company = client.post("/api/bi/companies", headers=owner, json={
        "name": "리본반도체 (데모)", "industry": "semiconductor", "main_products": ["DDR5 모듈", "HBM 패키징"],
        "interest_industries": ["AI 서버", "자동차 전장"], "trade_countries": ["미국", "일본", "대만"], "interest_indicators": [],
    }).json()
    cid = company["id"]
    for email, _, role in USERS[1:]:
        client.put(f"/api/bi/companies/{cid}/members", headers=owner, json={"email": email, "role": role}).raise_for_status()
    upload = client.post(f"/api/bi/companies/{cid}/erp/upload", headers=owner,
                         files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "text/csv")})
    upload.raise_for_status()
    fx = client.post("/api/bi/market/fx/collect", headers=owner)
    run = client.post(f"/api/bi/companies/{cid}/analyses", headers=owner).json()
    approver = tokens[USERS[1][0]]
    members = {m["email"]: m["id"] for m in client.get(f"/api/bi/companies/{cid}/members", headers=owner).json()}
    inventory = next((f for f in run["findings"] if "재고" in f["title"]), None)
    if inventory:
        client.post(f"/api/bi/companies/{cid}/findings/{inventory['id']}/decisions", headers=approver, json={
            "status": "APPROVED", "reason": "재고일수가 2개월 연속 기준을 넘어 생산 계획 조정이 필요함",
            "assignee_id": members[USERS[2][0]], "follow_up": "DDR5 모듈 11월 생산량 10% 감산안 작성", "due_date": None,
        }).raise_for_status()
    return {"company_id": cid, "rows": upload.json()["accepted"], "fx": fx.json(), "findings": len(run["findings"])}


if __name__ == "__main__":
    Base.metadata.create_all(get_engine())
    with TestClient(api) as client:
        print(seed(client))
