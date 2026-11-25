"""감사 추적 로그 — 읽기 전용, 수정/삭제 불가"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import AuditLog, User

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])


@router.get("")
def list_logs(action: str | None = None, user_name: str | None = None,
              days: int | None = None, limit: int = Query(100, le=500),
              offset: int = 0,
              user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(AuditLog).filter(AuditLog.company_id == user.company_id)
    if action:
        q = q.filter(AuditLog.action.like(f"%{action}%"))
    if user_name:
        q = q.filter(AuditLog.user_name.like(f"%{user_name}%"))
    if days:
        from datetime import datetime, timedelta
        q = q.filter(AuditLog.created_at >= datetime.utcnow() - timedelta(days=days))
    total = q.count()
    rows = q.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "items": [{
            "id": l.id, "user_name": l.user_name, "user_role": l.user_role,
            "action": l.action, "target_type": l.target_type,
            "target_id": l.target_id, "detail": l.detail,
            "created_at": l.created_at.isoformat() if l.created_at else "",
        } for l in rows],
        "note": "감사 로그는 시스템에 의해 자동 기록되며 수정·삭제할 수 없습니다.",
    }
