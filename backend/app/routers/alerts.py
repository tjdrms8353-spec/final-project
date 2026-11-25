"""알림 센터 — 위험 알림 + 알림(Notification) + 알림 설정"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_write
from ..models import Notification, NotificationSetting, RiskAlert, User
from ..schemas import NotificationSettingUpdate

router = APIRouter(prefix="/api", tags=["alerts"])

SEVERITY_ORDER = {"심각": 0, "위험": 1, "주의": 2, "관심": 3, "정상": 4}


@router.get("/alerts")
def list_alerts(status: str | None = None, severity: str | None = None,
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(RiskAlert).filter(RiskAlert.company_id == user.company_id)
    if status:
        q = q.filter(RiskAlert.status == status)
    if severity:
        q = q.filter(RiskAlert.severity == severity)
    rows = q.order_by(RiskAlert.created_at.desc()).limit(100).all()
    rows.sort(key=lambda a: (SEVERITY_ORDER.get(a.severity, 9),
                             a.created_at), reverse=False)
    return {
        "items": [{
            "id": a.id, "severity": a.severity, "category": a.category,
            "title": a.title, "message": a.message, "status": a.status,
            "related_type": a.related_type, "related_id": a.related_id,
            "created_at": a.created_at.isoformat() if a.created_at else "",
        } for a in rows],
        "severity_rules": {
            "fx": "환율 전월 대비: ≥2% 주의 / ≥4% 위험 / ≥6% 심각 (외화결제 비중 높으면 상향)",
            "op_margin": "영업이익률 전년동월 대비 하락: ≥2%p 주의 / ≥4%p 위험",
            "revenue": "매출 전년동기: <-2% 주의 / <-5% 위험",
            "material": "원자재비/매출 ≥62% 주의",
            "customer": "최대 거래처 의존도 ≥40% 관심",
        },
    }


@router.patch("/alerts/{alert_id}")
def update_alert(alert_id: int, body: dict, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    a = db.get(RiskAlert, alert_id)
    if not a or a.company_id != user.company_id:
        raise HTTPException(404, "알림을 찾을 수 없습니다.")
    status = body.get("status")
    if status not in ("unread", "read", "acknowledged"):
        raise HTTPException(400, "올바르지 않은 상태입니다.")
    a.status = status
    audit(db, user, "ALERT_UPDATE", "risk_alert", a.id, f"상태 → {status}")
    db.commit()
    return {"id": a.id, "status": a.status}


@router.get("/notifications")
def list_notifications(user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    rows = (
        db.query(Notification)
        .filter(Notification.company_id == user.company_id)
        .order_by(Notification.created_at.desc()).limit(100).all()
    )
    unread = sum(1 for n in rows if not n.is_read)
    return {
        "unread": unread,
        "items": [{
            "id": n.id, "ntype": n.ntype, "title": n.title, "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat() if n.created_at else "",
        } for n in rows],
    }


@router.patch("/notifications/{notif_id}/read")
def read_notification(notif_id: int, user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    n = db.get(Notification, notif_id)
    if not n or n.company_id != user.company_id:
        raise HTTPException(404, "알림을 찾을 수 없습니다.")
    n.is_read = True
    db.commit()
    return {"id": n.id, "is_read": True}


@router.post("/notifications/read-all")
def read_all_notifications(user: User = Depends(get_current_user),
                           db: Session = Depends(get_db)):
    rows = db.query(Notification).filter(
        Notification.company_id == user.company_id, Notification.is_read == False).all()  # noqa: E712
    for n in rows:
        n.is_read = True
    db.commit()
    return {"updated": len(rows)}


@router.get("/notification-settings")
def get_settings(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    st = db.query(NotificationSetting).filter(
        NotificationSetting.company_id == user.company_id).first()
    if not st:
        st = NotificationSetting(company_id=user.company_id)
        db.add(st)
        db.commit()
        db.refresh(st)
    return {
        "risk_alert": st.risk_alert, "important_news": st.important_news,
        "kpi_change": st.kpi_change, "analysis_done": st.analysis_done,
        "weekly_summary": st.weekly_summary,
        "email_enabled": st.email_enabled, "kakao_enabled": st.kakao_enabled,
        "email_address": st.email_address,
        "note": "외부 발송 API 미연결 데모: 실제 이메일/카카오 발송 없이 '발송 대기' 상태로 기록됩니다.",
    }


@router.put("/notification-settings")
def update_settings(body: NotificationSettingUpdate,
                    user: User = Depends(require_write), db: Session = Depends(get_db)):
    st = db.query(NotificationSetting).filter(
        NotificationSetting.company_id == user.company_id).first()
    if not st:
        st = NotificationSetting(company_id=user.company_id)
        db.add(st)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(st, k, v)
    audit(db, user, "SETTINGS_UPDATE", "notification_settings", st.id)
    db.commit()
    return get_settings(user, db)
