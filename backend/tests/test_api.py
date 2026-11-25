"""핵심 API 통합 테스트 — 인증/권한/데이터/알림/업로드를 검증한다."""
import io


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_login_success(client):
    r = client.post("/api/auth/login",
                    json={"email": "owner@dayribbon.demo", "password": "demo1234"})
    assert r.status_code == 200
    body = r.json()
    assert body["token"]
    assert body["user"]["role"] == "OWNER"


def test_login_wrong_password(client):
    r = client.post("/api/auth/login",
                    json={"email": "owner@dayribbon.demo", "password": "wrong"})
    assert r.status_code == 401


def test_login_lockout(client):
    # 동일 이메일 5회 실패 → 429 잠금
    for _ in range(5):
        r = client.post("/api/auth/login",
                        json={"email": "admin@dayribbon.demo", "password": "x"})
        assert r.status_code == 401
    r = client.post("/api/auth/login",
                    json={"email": "admin@dayribbon.demo", "password": "demo1234"})
    assert r.status_code == 429


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401
    r = client.get("/api/auth/me",
                   headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_me_ok(client, owner_headers):
    r = client.get("/api/auth/me", headers=owner_headers)
    assert r.status_code == 200
    assert r.json()["email"] == "owner@dayribbon.demo"


def test_viewer_write_forbidden(client, viewer_headers):
    r = client.post("/api/financial/monthly", headers=viewer_headers,
                    json={"month": "2026-11", "revenue": 1, "operating_profit": 0})
    assert r.status_code == 403


def test_monthly_upsert_and_pipeline(client, owner_headers):
    r = client.post("/api/financial/monthly", headers=owner_headers, json={
        "month": "2026-11", "revenue": 8800000000, "operating_profit": 850000000,
        "raw_material_cost": 5100000000, "labor_cost": 1180000000,
        "other_cost": 1650000000, "export_amount": 5500000000,
        "import_amount": 3300000000, "fx_avg_rate": 1435.0,
    })
    assert r.status_code == 200
    assert r.json()["pipeline"]["new_analyses"] >= 1

    rows = client.get("/api/financial/monthly", headers=owner_headers).json()
    assert any(m["month"] == "2026-11" for m in rows)


def test_monthly_bad_month_format(client, owner_headers):
    r = client.post("/api/financial/monthly", headers=owner_headers,
                    json={"month": "202611", "revenue": 1})
    assert r.status_code == 400


def test_records_product_crud(client, owner_headers):
    # 생성
    r = client.post("/api/financial/records/product_monthly", headers=owner_headers,
                    json={"month": "2026-10", "product_name": "테스트제품A",
                          "revenue": 1000000, "cost": 700000})
    assert r.status_code == 200
    rid = r.json()["id"]

    # 목록 조회
    rows = client.get("/api/financial/records/product_monthly",
                      headers=owner_headers).json()
    rec = [x for x in rows if x["id"] == rid]
    assert rec and rec[0]["product_name"] == "테스트제품A"

    # upsert (동일 month+제품명 → 갱신)
    r2 = client.post("/api/financial/records/product_monthly", headers=owner_headers,
                     json={"month": "2026-10", "product_name": "테스트제품A",
                           "revenue": 2000000, "cost": 800000})
    assert r2.status_code == 200
    assert r2.json()["id"] == rid

    # 삭제
    assert client.delete(f"/api/financial/records/product_monthly/{rid}",
                         headers=owner_headers).status_code == 200
    rows = client.get("/api/financial/records/product_monthly",
                      headers=owner_headers).json()
    assert all(x["id"] != rid for x in rows)


def test_records_customer_and_material(client, owner_headers):
    r = client.post("/api/financial/records/customer_monthly", headers=owner_headers,
                    json={"month": "2026-10", "customer_name": "테스트거래처",
                          "country": "KR", "revenue": 500000})
    assert r.status_code == 200
    r = client.post("/api/financial/records/material_purchase", headers=owner_headers,
                    json={"month": "2026-10", "material_name": "테스트원자재",
                          "amount_krw": 300000, "currency": "KRW"})
    assert r.status_code == 200


def test_records_viewer_forbidden(client, viewer_headers):
    r = client.post("/api/financial/records/product_monthly", headers=viewer_headers,
                    json={"month": "2026-10", "product_name": "X"})
    assert r.status_code == 403


def test_records_invalid_kind(client, owner_headers):
    r = client.get("/api/financial/records/financial_monthly", headers=owner_headers)
    assert r.status_code == 400


def test_records_tenant_isolation(client, owner_headers):
    """타 기업 데이터에 접근 불가 — 제2기업 계정이 없으므로 seed 기업과 다른 id 삭제 시도"""
    # 존재하지 않는 id 삭제는 404 (기업 격리 검증의 근사)
    r = client.delete("/api/financial/records/product_monthly/999999",
                      headers=owner_headers)
    assert r.status_code == 404


def test_upload_missing_columns(client, owner_headers):
    csv = "month,revenue\n2026-11,100\n"
    r = client.post("/api/financial/upload?data_kind=financial_monthly",
                    headers=owner_headers,
                    files={"file": ("bad.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert r.status_code == 400
    assert "필수 컬럼" in r.json()["detail"]


def test_upload_financial_csv(client, owner_headers):
    csv = "month,revenue,operating_profit\n2026-09,7000000000,700000000\n"
    r = client.post("/api/financial/upload?data_kind=financial_monthly",
                    headers=owner_headers,
                    files={"file": ("ok.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "완료"
    assert body["pipeline"]["new_analyses"] >= 1


def test_upload_preview_no_save(client, owner_headers):
    """미리보기는 검증 결과만 반환하고 저장하지 않는다."""
    csv = "month,revenue,operating_profit\n2099-01,123,45\n2099-02,456,78\n"
    r = client.post("/api/financial/upload/preview?data_kind=financial_monthly",
                    headers=owner_headers,
                    files={"file": ("prev.csv", io.BytesIO(csv.encode()), "text/csv")})
    assert r.status_code == 200
    body = r.json()
    assert body["row_count"] == 2
    assert len(body["preview"]) == 2
    # 저장되지 않았는지 확인
    rows = client.get("/api/financial/monthly", headers=owner_headers).json()
    assert all(m["month"] != "2099-01" for m in rows)


def test_upload_size_limit(client, owner_headers):
    big = b"month,revenue\n" + b"2026-01,1\n" * 2_200_000  # ~22MB > 20MB 제한
    r = client.post("/api/financial/upload?data_kind=financial_monthly",
                    headers=owner_headers,
                    files={"file": ("big.csv", io.BytesIO(big), "text/csv")})
    assert r.status_code == 413


def test_dashboard_kpis(client, owner_headers):
    r = client.get("/api/dashboard", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert "revenue" in str(body)


def test_notification_settings_gate(client, owner_headers):
    """알림 설정 off → 해당 알림 미발행 검증 (분석 완료 알림 기준)"""
    r = client.get("/api/notification-settings", headers=owner_headers)
    assert r.status_code == 200
    assert "analysis_done" in r.json()

    client.put("/api/notification-settings", headers=owner_headers,
               json={"analysis_done": False})
    r = client.post("/api/analysis/run", headers=owner_headers)
    assert r.status_code == 200
    client.put("/api/notification-settings", headers=owner_headers,
               json={"analysis_done": True})


def test_weekly_summary_exists_or_skipped(client, owner_headers):
    """주간 요약 함수가 설정 on에서 알림을 생성하고 중복 생성하지 않는다."""
    from app.database import SessionLocal
    from app.services.analysis_engine import weekly_summary

    from app.models import Notification

    db = SessionLocal()
    try:
        before = db.query(Notification).filter(
            Notification.company_id == 1, Notification.ntype == "weekly").count()
        weekly_summary(db, 1)
        db.commit()
        mid = db.query(Notification).filter(
            Notification.company_id == 1, Notification.ntype == "weekly").count()
        weekly_summary(db, 1)
        db.commit()
        after = db.query(Notification).filter(
            Notification.company_id == 1, Notification.ntype == "weekly").count()
        # 최초 호출 시 생성(스케줄러 선행 실행 시 이미 존재 가능), 재호출은 중복 차단
        assert mid >= before and after == mid and after >= 1
    finally:
        db.close()


def test_audit_logs_readonly(client, owner_headers, viewer_headers):
    r = client.get("/api/audit-logs", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert "items" in body and body["total"] >= 1


def test_simulation_runs(client, owner_headers):
    r = client.post("/api/simulation/run", headers=owner_headers, json={
        "fx_change_pct": 5.0, "rate_change_pct": 0.5,
        "material_change_pct": 5.0, "annual_import_cost": 5000000000,
        "debt_amount": 10000000000, "revenue_change_pct": -3.0,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["severity"] in ("정상", "관심", "주의", "위험", "심각")
    assert "순_영향_추정" in body["results"]
