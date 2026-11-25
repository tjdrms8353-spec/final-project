from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user
from ..models import AuthToken, User
from ..schemas import LoginRequest
from ..security import generate_token, hash_token, token_expiry, verify_password

auth_router = APIRouter(prefix="/api/auth", tags=["auth"])

# 로그인 실패 잠금: 이메일별 실패 카운트 (인메모리, 데모 규모 충분)
_LOGIN_FAILS: dict[str, list[datetime]] = {}
MAX_FAILS = 5
LOCK_WINDOW_MIN = 15


def _check_lock(email: str):
    now = datetime.utcnow()
    fails = [t for t in _LOGIN_FAILS.get(email, [])
             if (now - t).total_seconds() < LOCK_WINDOW_MIN * 60]
    _LOGIN_FAILS[email] = fails
    if len(fails) >= MAX_FAILS:
        raise HTTPException(429, f"로그인 실패가 {MAX_FAILS}회 초과하여 {LOCK_WINDOW_MIN}분간 잠겼습니다.")


def _record_fail(email: str):
    _LOGIN_FAILS.setdefault(email, []).append(datetime.utcnow())


def user_dict(u: User, db: Session) -> dict:
    return {
        "id": u.id, "email": u.email, "name": u.name, "role": u.role,
        "company_id": u.company_id, "company_name": u.company.name if u.company else "",
        "is_active": u.is_active,
    }


@auth_router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    _check_lock(body.email)
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        _record_fail(body.email)
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다.")
    if not user.is_active:
        raise HTTPException(403, "비활성화된 계정입니다.")
    _LOGIN_FAILS.pop(body.email, None)
    token = generate_token()
    db.add(AuthToken(token=hash_token(token), user_id=user.id, expires_at=token_expiry()))
    audit(db, user, "LOGIN", "user", user.id)
    db.commit()
    return {"token": token, "user": user_dict(user, db)}


@auth_router.post("/logout")
def logout(request: Request, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        rec = db.get(AuthToken, hash_token(auth[7:].strip()))
        if rec:
            db.delete(rec)
    audit(db, user, "LOGOUT", "user", user.id)
    db.commit()
    return {"ok": True}


@auth_router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return user_dict(user, db)
