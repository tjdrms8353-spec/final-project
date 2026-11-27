from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from datetime import timedelta

from ..database import get_db
from ..deps import audit, get_current_user
from ..models import AuthToken, PasswordResetToken, User
from ..schemas import (
    LoginRequest, PasswordChange, PasswordResetConfirm,
    PasswordResetRequest, RegisterRequest,
)
from ..security import (
    generate_token, hash_password, hash_token, token_expiry, verify_password,
)

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


@auth_router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """회원가입 — 이메일 중복 검사 후 기업 미소속 상태로 계정 생성.

    생성 직후 로그인 토큰도 함께 발급한다. 이후 흐름은 온보딩(기업 등록 또는
    초대 수락)에서 진행한다.
    """
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, "이미 가입된 이메일입니다.")
    user = User(email=email, password_hash=hash_password(body.password),
                name=body.name.strip(), company_id=None, role="MEMBER")
    db.add(user)
    db.flush()
    audit(db, user, "REGISTER", "user", user.id, f"회원가입: {email}")
    token = generate_token()
    db.add(AuthToken(token=hash_token(token), user_id=user.id, expires_at=token_expiry()))
    db.commit()
    return {"token": token, "user": user_dict(user, db)}


@auth_router.post("/change-password")
def change_password(body: PasswordChange, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(400, "현재 비밀번호가 올바르지 않습니다.")
    user.password_hash = hash_password(body.new_password)
    # 기존 세션 전부 무효화
    db.query(AuthToken).filter(AuthToken.user_id == user.id).delete()
    audit(db, user, "PASSWORD_CHANGE", "user", user.id)
    db.commit()
    return {"ok": True, "message": "비밀번호가 변경되었습니다. 다시 로그인하세요."}


@auth_router.post("/password-reset/request")
def password_reset_request(body: PasswordResetRequest, db: Session = Depends(get_db)):
    """비밀번호 재설정 요청. 이메일 발송 모듈 미연동 — 토큰을 생성하고
    응답에 포함해 반환한다(발송 연동 시 응답에서 제거 예정)."""
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    msg = "해당 이메일로 재설정 안내를 발송했습니다(이메일 미연동 데모: 실제 발송 없음)."
    if not user:
        # 계정 존재 여부를 응답으로 노출하지 않음
        return {"ok": True, "message": msg, "demo_reset_token": None}
    token = generate_token()
    db.add(PasswordResetToken(
        token_hash=hash_token(token), user_id=user.id,
        expires_at=datetime.utcnow() + timedelta(hours=1)))
    # 재설정 안내 이메일을 발송 큐에 적재 — 기업 미소속 계정도 가능(company_id NULL).
    # SMTP 미설정이면 '발송 대기'로 남고 설정 후 자동 발송된다.
    from ..services.delivery_service import enqueue_delivery
    enqueue_delivery(
        db, user.company_id, "email", user.email,
        "[dayribbon] 비밀번호 재설정 안내",
        "비밀번호 재설정을 요청했습니다.\n\n"
        f"재설정 토큰: {token}\n\n"
        "'비밀번호 찾기' 화면의 재설정 확인 단계에 이 토큰을 입력하세요. "
        "1시간 동안 유효하며, 본인이 요청하지 않았다면 이 메일을 무시하셔도 됩니다.")
    db.commit()
    # SMTP 미설정 대비 — 테스트 편의로 토큰을 응답에도 포함(실발송 확인 후 제거 검토)
    return {"ok": True, "message": msg, "demo_reset_token": token,
            "note": "재설정 안내가 발송 큐에 등록되었습니다. SMTP 미설정 시 대기 상태로 남습니다."}


@auth_router.post("/password-reset/confirm")
def password_reset_confirm(body: PasswordResetConfirm, db: Session = Depends(get_db)):
    rec = db.get(PasswordResetToken, hash_token(body.token.strip()))
    if (not rec or rec.used or rec.expires_at < datetime.utcnow()):
        raise HTTPException(400, "재설정 토큰이 만료되었거나 유효하지 않습니다.")
    user = db.get(User, rec.user_id)
    if not user:
        raise HTTPException(400, "사용자를 찾을 수 없습니다.")
    user.password_hash = hash_password(body.new_password)
    rec.used = True
    db.query(AuthToken).filter(AuthToken.user_id == user.id).delete()
    audit(db, user, "PASSWORD_RESET", "user", user.id)
    db.commit()
    return {"ok": True, "message": "비밀번호가 재설정되었습니다. 새 비밀번호로 로그인하세요."}
