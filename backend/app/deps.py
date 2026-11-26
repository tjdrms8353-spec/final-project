from datetime import datetime

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .database import get_db
from .models import AuthToken, User

ROLE_ORDER = {"VIEWER": 0, "MEMBER": 1, "ADMIN": 2, "OWNER": 3}

WRITE_ROLES = {"OWNER", "ADMIN", "MEMBER"}
ADMIN_ROLES = {"OWNER", "ADMIN"}


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "인증 토큰이 없습니다. 로그인 후 다시 시도하세요.")
    token = auth[7:].strip()
    from .security import hash_token
    rec = db.get(AuthToken, hash_token(token))
    if rec is None or rec.expires_at < datetime.utcnow():
        raise HTTPException(401, "인증 토큰이 만료되었거나 유효하지 않습니다.")
    user = db.get(User, rec.user_id)
    if user is None or not user.is_active:
        raise HTTPException(401, "사용자 계정을 찾을 수 없습니다.")
    return user


def require_role(*roles: str):
    allowed = set(roles)

    def checker(user: User = Depends(get_current_user)):
        if user.role not in allowed:
            raise HTTPException(403, f"권한이 없습니다. 필요 권한: {', '.join(sorted(allowed))}")
        return user

    return checker


def require_write(user: User = Depends(get_current_user)) -> User:
    if user.role not in WRITE_ROLES:
        raise HTTPException(403, "읽기 전용(VIEWER) 권한으로는 수정 작업을 수행할 수 없습니다.")
    if not user.company_id:
        raise HTTPException(400, "소속 기업이 없습니다. 기업을 등록하거나 초대를 수락하세요.")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ADMIN_ROLES:
        raise HTTPException(403, "관리자(ADMIN/OWNER) 권한이 필요합니다.")
    return user


def audit(db: Session, user: User | None, action: str, target_type: str = "",
          target_id: str = "", detail: str = ""):
    from .models import AuditLog
    log = AuditLog(
        # 기업 미등록 사용자는 company_id=None — FK 대상이 없으므로 NULL 저장
        company_id=user.company_id if user else None,
        user_id=user.id if user else None,
        user_name=user.name if user else "(시스템)",
        user_role=user.role if user else "",
        action=action,
        target_type=target_type,
        target_id=str(target_id),
        detail=detail[:2000],
    )
    db.add(log)
