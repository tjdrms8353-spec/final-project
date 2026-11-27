"""정식 전환 D — 알림 실발송 큐·어댑터·운영 상태 API 테스트."""
import pytest

from app.models import NotificationDelivery, NotificationSetting, User
from app.services import delivery_service as ds


@pytest.fixture(autouse=True)
def _clean_deliveries(db):
    """발송 큐를 비워 테스트 간 격리한다."""
    db.query(NotificationDelivery).delete()
    db.commit()


def _get_settings(db, company_id):
    st = db.query(NotificationSetting).filter(
        NotificationSetting.company_id == company_id).first()
    if not st:
        st = NotificationSetting(company_id=company_id)
        db.add(st)
        db.flush()
    return st


def test_enqueue_and_skip_without_address(db):
    st = _get_settings(db, 1)
    st.email_enabled = True
    st.email_address = "ops@test.com"
    d = ds.queue_company_notifications(db, 1, "위험 알림", "메시지 본문")
    assert len(d) == 1 and d[0].channel == "email"
    assert d[0].status == "pending" and d[0].address == "ops@test.com"

    st.email_address = ""     # 주소 비우면 OWNER/ADMIN 계정 메일로 폴백
    d2 = ds.queue_company_notifications(db, 1, "제목", "본문")
    addrs = {d.address for d in d2}
    assert addrs and all(d.status == "pending" for d in d2)
    assert "owner@dayribbon.demo" in addrs


def test_channel_toggles(db):
    st = _get_settings(db, 1)
    st.email_enabled, st.kakao_enabled = False, True
    st.email_address = "a@b.com"; st.kakao_phone = "01000000000"
    d = ds.queue_company_notifications(db, 1, "t", "m")
    assert [x.channel for x in d] == ["kakao"]

    st.email_enabled, st.kakao_enabled = True, False
    d2 = ds.queue_company_notifications(db, 1, "t", "m")
    assert [x.channel for x in d2] == ["email"]


def test_unconfigured_stays_pending(db):
    """이메일 미설정 시 pending 유지 — 시도 횟수를 소비하지 않는다."""
    assert not ds.email_configured()      # 테스트 환경에는 이메일 설정 없음
    ds.enqueue_delivery(db, 1, "email", "a@b.com", "t", "m")
    db.flush()
    r = ds.process_pending_deliveries(db)
    d = db.query(NotificationDelivery).one()
    assert r["waiting"] == 1
    assert d.status == "pending" and d.attempts == 0
    assert "SMTP" in d.last_error


def test_email_send_success(db, monkeypatch):
    monkeypatch.setattr(ds, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(ds, "SMTP_PORT", 587)
    monkeypatch.setattr(ds, "SMTP_USER", "u")
    monkeypatch.setattr(ds, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(ds, "SMTP_STARTTLS", True)

    sent = []

    class FakeSMTP:
        def __init__(self, host, port, timeout=0):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
        def starttls(self):
            sent.append("tls")
        def login(self, u, p):
            sent.append("login")
        def send_message(self, msg):
            sent.append(msg["To"])

    monkeypatch.setattr(ds.smtplib, "SMTP", FakeSMTP)
    ds.enqueue_delivery(db, 1, "email", "to@co.kr", "제목", "본문")
    db.flush()
    r = ds.process_pending_deliveries(db)
    d = db.query(NotificationDelivery).one()
    assert r["sent"] == 1 and d.status == "sent" and d.sent_at is not None
    assert "to@co.kr" in sent and "tls" in sent and "login" in sent


def test_email_send_resend(db, monkeypatch):
    """RESEND_API_KEY 설정 시 SMTP 대신 Resend HTTPS API로 발송."""
    monkeypatch.setattr(ds, "RESEND_API_KEY", "re_test")
    calls = []

    class FakeResp:
        status_code = 200
        text = "{}"

    def fake_post(url, headers=None, json=None, timeout=0):
        calls.append((url, headers, json))
        return FakeResp()

    monkeypatch.setattr(ds.httpx, "post", fake_post)
    ds.enqueue_delivery(db, 1, "email", "to@co.kr", "제목", "본문")
    db.flush()
    r = ds.process_pending_deliveries(db)
    d = db.query(NotificationDelivery).one()
    assert r["sent"] == 1 and d.status == "sent"
    url, headers, payload = calls[0]
    assert "api.resend.com" in url
    assert headers["Authorization"] == "Bearer re_test"
    assert payload["to"] == ["to@co.kr"]
    assert "html" in payload and "제목" in payload["subject"]


def test_weekly_summary_queues_email(db):
    """주간 요약 생성 시 이메일 발송 건도 큐에 적재된다 (OWNER/ADMIN 폴백)."""
    from app.models import Notification
    from app.services.analysis_engine import weekly_summary
    # 세션 공유 DB — 시드/이전 테스트의 주간 알림이 중복 차단을 유발하므로 제거
    db.query(Notification).filter(Notification.ntype == "weekly").delete()
    db.commit()
    n = weekly_summary(db, 1)
    assert n is not None
    db.flush()   # SessionLocal은 autoflush=False — 조회 전 명시적 플러시 필요
    ds = db.query(NotificationDelivery).filter(
        NotificationDelivery.title == "주간 경영 요약").all()
    assert ds and all(d.channel == "email" and d.address for d in ds)


def test_monthly_report_dispatch(db):
    """월간 보고서 자동 생성 + 이메일 큐 등록. 재호출 시 중복 생성 없음."""
    from app.models import Report
    from app.services.report_service import dispatch_monthly_reports
    reps = dispatch_monthly_reports(db)
    assert len(reps) >= 1
    period = reps[0].period
    assert db.query(NotificationDelivery).filter(
        NotificationDelivery.title.like(f"%{period} 월간 경영 보고서%")).count() >= 1
    before = db.query(Report).count()
    assert dispatch_monthly_reports(db) == []
    assert db.query(Report).count() == before


def test_email_failure_retry_then_failed(db, monkeypatch):
    monkeypatch.setattr(ds, "SMTP_HOST", "smtp.test")
    monkeypatch.setattr(ds, "SMTP_USER", "u")
    monkeypatch.setattr(ds, "SMTP_PASSWORD", "p")
    monkeypatch.setattr(ds, "DELIVERY_MAX_ATTEMPTS", 2)

    class BoomSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def starttls(self): pass
        def login(self, u, p): raise OSError("auth fail")

    monkeypatch.setattr(ds.smtplib, "SMTP", BoomSMTP)
    ds.enqueue_delivery(db, 1, "email", "a@b.com", "t", "m")
    db.flush()
    ds.process_pending_deliveries(db)
    d = db.query(NotificationDelivery).one()
    assert d.status == "pending" and d.attempts == 1 and "auth fail" in d.last_error
    ds.process_pending_deliveries(db)   # attempts=2
    ds.process_pending_deliveries(db)   # 상한 도달 → failed
    assert db.query(NotificationDelivery).one().status == "failed"


def test_kakao_unconfigured(db):
    assert not ds.kakao_configured()
    ok, err = ds.send_kakao("01012345678", "t", "m")
    assert ok is False and "카카오" in err


def test_deliveries_api(db, client, owner_headers):
    owner = db.query(User).filter(User.email == "owner@dayribbon.demo").one()
    ds.enqueue_delivery(db, owner.company_id, "email", "ops@test.com",
                        "알림 제목", "본문")
    db.commit()
    r = client.get("/api/deliveries", headers=owner_headers)
    assert r.status_code == 200
    items = r.json()["items"]
    assert len(items) == 1 and items[0]["channel"] == "email"
    assert items[0]["address"] == "ops@test.com"


def test_invite_queues_email(db, client, owner_headers):
    """초대 생성 시 안내 이메일이 발송 큐에 적재된다."""
    r = client.post("/api/invites", headers=owner_headers,
                    json={"email": "newbie@test.com", "role": "MEMBER"})
    assert r.status_code == 200
    d = db.query(NotificationDelivery).filter_by(
        channel="email", address="newbie@test.com").one()
    assert d.status == "pending" and "초대" in d.title
    assert d.company_id is not None   # 초대는 기업 소속 발송


def test_password_reset_queues_email(db, client):
    """재설정 요청 시 이메일이 큐에 적재 — 기업 미소속 계정도 NULL로 가능."""
    client.post("/api/auth/register",
                json={"email": "resetme@test.com", "password": "password123", "name": "R"})
    r = client.post("/api/auth/password-reset/request",
                    json={"email": "resetme@test.com"})
    assert r.status_code == 200
    d = db.query(NotificationDelivery).filter_by(address="resetme@test.com").one()
    assert d.company_id is None and "재설정" in d.title


def test_ops_test_delivery(client, owner_headers, viewer_headers):
    r = client.post("/api/ops/test-delivery", headers=owner_headers,
                    json={"channel": "email", "address": "ops@test.com"})
    assert r.status_code == 200
    assert r.json()["status"] == "pending"     # SMTP 미설정 → 대기
    # 잘못된 채널 거부
    r = client.post("/api/ops/test-delivery", headers=owner_headers,
                    json={"channel": "sms", "address": "01012345678"})
    assert r.status_code == 422
    # 관리자 아니면 403
    r = client.post("/api/ops/test-delivery", headers=viewer_headers,
                    json={"channel": "email", "address": "ops@test.com"})
    assert r.status_code == 403


def test_ops_status_admin_only(db, client, owner_headers, viewer_headers):
    r = client.get("/api/ops/status", headers=viewer_headers)
    assert r.status_code == 403
    r = client.get("/api/ops/status", headers=owner_headers)
    assert r.status_code == 200
    body = r.json()
    assert "deliveries" in body and "email_configured" in body["deliveries"]
    assert body["deliveries"]["email_configured"] is False
    assert "collectors" in body and "llm_month" in body
