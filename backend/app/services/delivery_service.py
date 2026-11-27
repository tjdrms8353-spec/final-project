"""알림 실발송 서비스 — 이메일(Resend/SMTP)·카카오 알림톡 어댑터 + 발송 큐 처리.

- 인앱 Notification과 별개로 NotificationDelivery 큐에 외부 발송 건을 적재한다.
- 발송 채널 설정(RESEND_API_KEY, SMTP_*, KAKAO_*)이 없으면 큐에 'pending'으로 남고
  last_error에 미설정 사유가 기록된다 — 설정 후 다음 워커 실행 때 자동 발송.
- 재시도는 DELIVERY_MAX_ATTEMPTS까지, 초과 시 'failed'.
"""
import base64
import html as _html
import os
import smtplib
from datetime import datetime
from email.message import EmailMessage

import httpx
from sqlalchemy.orm import Session

from ..config import (
    DELIVERY_MAX_ATTEMPTS, KAKAO_API_KEY, KAKAO_API_URL, KAKAO_SENDER_KEY,
    RESEND_API_KEY, RESEND_FROM,
    SMTP_FROM, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_STARTTLS, SMTP_USER,
)
from ..models import NotificationDelivery, NotificationSetting

UNCONFIGURED_EMAIL = "이메일 미설정 — RESEND_API_KEY 또는 SMTP_HOST·SMTP_USER·SMTP_PASSWORD 필요"
UNCONFIGURED_KAKAO = "카카오 알림톡 미설정 — KAKAO_API_URL·KAKAO_API_KEY 필요"

RESEND_API_URL = "https://api.resend.com/emails"


def resend_configured() -> bool:
    return bool(RESEND_API_KEY)


def smtp_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


def email_configured() -> bool:
    return resend_configured() or smtp_configured()


def kakao_configured() -> bool:
    return bool(KAKAO_API_URL and KAKAO_API_KEY)


def send_email(address: str, title: str, message: str,
               attachments: list[tuple[str, bytes]] | None = None) -> tuple[bool, str]:
    """이메일 발송. RESEND_API_KEY가 있으면 Resend(HTTPS), 아니면 SMTP.

    attachments: (파일명, 바이트) 튜플 목록 — 보고서 PDF 등.
    """
    if resend_configured():
        return _send_email_resend(address, title, message, attachments)
    if not smtp_configured():
        return False, UNCONFIGURED_EMAIL
    return _send_email_smtp(address, title, message, attachments)


def _send_email_resend(address: str, title: str, message: str,
                       attachments: list[tuple[str, bytes]] | None) -> tuple[bool, str]:
    """Resend HTTPS API로 발송 — Render 무료 플랜의 SMTP 포트 차단 우회."""
    body = _html.escape(message).replace("\n", "<br>")
    payload = {
        "from": RESEND_FROM or "dayribbon <onboarding@resend.dev>",
        "to": [address],
        "subject": f"[dayribbon] {title}",
        "text": message,
        "html": f'<div style="font-family:sans-serif;font-size:14px;line-height:1.6">{body}</div>',
    }
    if attachments:
        payload["attachments"] = [
            {"filename": fn, "content": base64.b64encode(data).decode()}
            for fn, data in attachments
        ]
    try:
        r = httpx.post(
            RESEND_API_URL,
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json=payload,
            timeout=30,
        )
        if r.status_code in (200, 201):
            return True, ""
        return False, f"Resend HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:500]


def _send_email_smtp(address: str, title: str, message: str,
                     attachments: list[tuple[str, bytes]] | None) -> tuple[bool, str]:
    """SMTP로 이메일 발송. (성공여부, 오류메시지) 반환."""
    msg = EmailMessage()
    msg["Subject"] = f"[dayribbon] {title}"
    msg["From"] = SMTP_FROM or SMTP_USER
    msg["To"] = address
    msg.set_content(message)
    for fn, data in attachments or []:
        subtype = "pdf" if fn.lower().endswith(".pdf") else "octet-stream"
        msg.add_attachment(data, maintype="application", subtype=subtype, filename=fn)
    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
                if SMTP_STARTTLS:
                    s.starttls()
                s.login(SMTP_USER, SMTP_PASSWORD)
                s.send_message(msg)
        return True, ""
    except Exception as e:  # SMTP 오류·네트워크 오류 등
        return False, f"{type(e).__name__}: {e}"[:500]


def send_kakao(phone: str, title: str, message: str) -> tuple[bool, str]:
    """카카오 알림톡 발송 (벤더 REST API). (성공여부, 오류메시지) 반환.

    벤더마다 요청 형식이 달라 KAKAO_API_URL로 엔드포인트를 주입한다.
    """
    if not kakao_configured():
        return False, UNCONFIGURED_KAKAO
    try:
        r = httpx.post(
            KAKAO_API_URL,
            json={
                "apikey": KAKAO_API_KEY,
                "sender_key": KAKAO_SENDER_KEY,
                "receiver": phone,
                "subject": f"[dayribbon] {title}",
                "message": message,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return True, ""
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:500]


def _email_recipients(db: Session, company_id: int | None) -> list[str]:
    """이메일 수신 주소 — 알림설정 email_address 우선, 없으면 기업 OWNER/ADMIN 계정."""
    st = (db.query(NotificationSetting)
          .filter(NotificationSetting.company_id == company_id).first())
    if st and st.email_address:
        return [st.email_address]
    if company_id:
        from ..models import User
        return [u.email for u in db.query(User).filter(
            User.company_id == company_id,
            User.role.in_(["OWNER", "ADMIN"]),
            User.is_active == True,  # noqa: E712
        ).limit(3)]
    return []


def enqueue_delivery(db: Session, company_id: int, channel: str, address: str,
                     title: str, message: str,
                     notification_id: int | None = None,
                     attachment_path: str = "") -> NotificationDelivery:
    """발송 큐에 등록. 수신 주소가 없으면 skipped로 기록한다."""
    d = NotificationDelivery(
        company_id=company_id, notification_id=notification_id,
        channel=channel, address=address or "", title=title[:300],
        message=message, attachment_path=attachment_path,
        status="pending" if address else "skipped",
        last_error="" if address else "수신 주소 없음",
    )
    db.add(d)
    return d


def process_pending_deliveries(db: Session, limit: int = 20) -> dict:
    """pending 발송 건을 처리한다. 미설정 채널은 시도 횟수를 올리지 않고 대기 유지."""
    rows = (db.query(NotificationDelivery)
            .filter(NotificationDelivery.status == "pending")
            .order_by(NotificationDelivery.created_at)
            .limit(limit).all())
    counts = {"sent": 0, "failed": 0, "waiting": 0}
    for d in rows:
        if d.attempts >= DELIVERY_MAX_ATTEMPTS:
            d.status = "failed"
            d.last_error = d.last_error or "재시도 상한 초과"
            counts["failed"] += 1
            continue
        if d.channel == "email":
            attachments = None
            if d.attachment_path and os.path.exists(d.attachment_path):
                attachments = [(os.path.basename(d.attachment_path),
                                open(d.attachment_path, "rb").read())]
            ok, err = send_email(d.address, d.title, d.message, attachments)
        elif d.channel == "kakao":
            ok, err = send_kakao(d.address, d.title, d.message)
        else:
            ok, err = False, f"알 수 없는 채널: {d.channel}"
        if ok:
            d.status = "sent"
            d.sent_at = datetime.utcnow()
            d.last_error = ""
            counts["sent"] += 1
        elif err in (UNCONFIGURED_EMAIL, UNCONFIGURED_KAKAO):
            d.last_error = err   # 미설정 — 대기 유지, 재시도 소비 안 함
            counts["waiting"] += 1
        else:
            d.attempts += 1
            d.last_error = err
            counts["waiting"] += 1
    return counts


def queue_company_notifications(db: Session, company_id: int,
                                title: str, message: str,
                                notification_id: int | None = None) -> list[NotificationDelivery]:
    """기업 알림 설정에 따라 이메일·카카오 발송 건을 큐에 넣는다."""
    st = (db.query(NotificationSetting)
          .filter(NotificationSetting.company_id == company_id).first())
    out = []
    email_on = st.email_enabled if st else True
    kakao_on = st.kakao_enabled if st else False
    if email_on:
        for addr in _email_recipients(db, company_id):
            out.append(enqueue_delivery(
                db, company_id, "email", addr,
                title, message, notification_id))
        if not out:
            out.append(enqueue_delivery(
                db, company_id, "email", "",
                title, message, notification_id))
    if kakao_on and st:
        out.append(enqueue_delivery(
            db, company_id, "kakao", st.kakao_phone,
            title, message, notification_id))
    return out
