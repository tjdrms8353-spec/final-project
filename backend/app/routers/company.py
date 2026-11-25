from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_admin, require_write
from ..models import (
    Company, CompanyInvite, Membership, NotificationSetting, User,
)
from ..schemas import (
    CompanyCreate, CompanySelect, CompanyUpdate, InviteAccept, InviteCreate,
    UserUpdate,
)
from ..security import generate_token, hash_token
from ..utils import fmt_krw

company_router = APIRouter(prefix="/api", tags=["company"])

VALID_ROLES = {"OWNER", "ADMIN", "MEMBER", "VIEWER"}
INVITABLE_ROLES = {"ADMIN", "MEMBER", "VIEWER"}  # OWNER는 초대로 부여 불가
INVITE_TTL_DAYS = 7


def company_dict(c: Company) -> dict:
    return {
        "id": c.id, "name": c.name, "industry": c.industry, "size": c.size,
        "products": c.products, "key_customers": c.key_customers,
        "export_countries": c.export_countries, "import_countries": c.import_countries,
        "raw_materials": c.raw_materials, "export_import_ratio": c.export_import_ratio,
        "annual_revenue": c.annual_revenue, "annual_raw_material_cost": c.annual_raw_material_cost,
        "fx_settlement_ratio": c.fx_settlement_ratio,
        "interest_areas": c.interest_areas, "risk_concerns": c.risk_concerns,
        "allow_external_ai": c.allow_external_ai,
        "annual_revenue_fmt": fmt_krw(c.annual_revenue),
        "annual_raw_material_cost_fmt": fmt_krw(c.annual_raw_material_cost),
    }


def invite_dict(i: CompanyInvite) -> dict:
    return {
        "id": i.id, "email": i.email, "role": i.role, "status": i.status,
        "invited_by": i.invited_by,
        "created_at": i.created_at.isoformat() if i.created_at else "",
        "expires_at": i.expires_at.isoformat() if i.expires_at else "",
    }


def _membership(db: Session, user_id: int, company_id: int) -> Membership | None:
    return db.query(Membership).filter(
        Membership.user_id == user_id,
        Membership.company_id == company_id).first()


def _activate_company(user: User, membership: Membership):
    """활성 기업 전환 — users.company_id/role을 소속 관계와 동기화."""
    user.company_id = membership.company_id
    user.role = membership.role


@company_router.post("/companies")
def create_company(body: CompanyCreate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """기업 워크스페이스 등록 — 생성자에게 OWNER 소속을 부여한다.

    데모 데이터는 일절 생성하지 않는다. 신규 기업은 빈 상태에서 시작한다.
    """
    c = Company(**body.model_dump())
    db.add(c)
    db.flush()
    m = Membership(user_id=user.id, company_id=c.id, role="OWNER")
    db.add(m)
    db.add(NotificationSetting(company_id=c.id))
    _activate_company(user, m)
    audit(db, user, "COMPANY_CREATE", "company", c.id, f"기업 등록: {c.name}")
    db.commit()
    return {"company": company_dict(c), "role": "OWNER"}


@company_router.get("/companies/mine")
def my_companies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """소속 기업 목록 (기업 선택 화면용)."""
    rows = (
        db.query(Membership, Company)
        .join(Company, Company.id == Membership.company_id)
        .filter(Membership.user_id == user.id)
        .all()
    )
    return [
        {"company_id": c.id, "name": c.name, "role": m.role,
         "active": c.id == user.company_id}
        for m, c in rows
    ]


@company_router.post("/companies/select")
def select_company(body: CompanySelect, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """활성 기업 전환 — 소속 관계가 없으면 거부한다(클라이언트 입력만으로 접근 불가)."""
    m = _membership(db, user.id, body.company_id)
    if not m:
        raise HTTPException(403, "해당 기업에 소속되어 있지 않습니다.")
    _activate_company(user, m)
    audit(db, user, "COMPANY_SELECT", "company", m.company_id)
    db.commit()
    return {"company_id": m.company_id, "role": m.role}


@company_router.get("/company")
def get_company(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.company:
        raise HTTPException(404, "소속 기업이 없습니다. 기업을 등록하거나 초대를 수락하세요.")
    return company_dict(user.company)


@company_router.put("/company")
def update_company(body: CompanyUpdate, user: User = Depends(require_write),
                   db: Session = Depends(get_db)):
    c = user.company
    if not c:
        raise HTTPException(404, "소속 기업이 없습니다.")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    audit(db, user, "COMPANY_UPDATE", "company", c.id, f"수정 항목: {', '.join(data.keys())}")
    db.commit()
    # 프로필 변경 → 자동 재분석 트리거 (지시서 §18). 사용자 직접 변경이므로 강제 실행.
    try:
        from ..services.analysis_engine import run_pipeline
        run_pipeline(db, c.id, trigger="profile", force=True)
        db.commit()
    except Exception:
        db.rollback()   # 재분석 실패가 프로필 저장을 실패시키지 않음
    return company_dict(c)


@company_router.get("/users")
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not user.company_id:
        return []
    rows = (
        db.query(User, Membership)
        .join(Membership, Membership.user_id == User.id)
        .filter(Membership.company_id == user.company_id)
        .all()
    )
    return [{"id": u.id, "email": u.email, "name": u.name, "role": m.role,
             "is_active": u.is_active} for u, m in rows]


@company_router.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate,
                actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    target_m = _membership(db, user_id, actor.company_id) if actor.company_id else None
    if not target or not target_m:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)

    if "role" in data:
        new_role = data["role"]
        if new_role not in VALID_ROLES:
            raise HTTPException(400, "올바르지 않은 권한 값입니다.")
        # OWNER 보호: OWNER 변경·부여는 OWNER만 가능
        if target_m.role == "OWNER" and actor.role != "OWNER":
            raise HTTPException(403, "OWNER 권한 사용자는 OWNER만 변경할 수 있습니다.")
        if new_role == "OWNER" and actor.role != "OWNER":
            raise HTTPException(403, "OWNER 권한은 OWNER만 부여할 수 있습니다.")
        target_m.role = new_role
        if target.company_id == actor.company_id:
            target.role = new_role  # 활성 기업 권한 동기화
    if "name" in data and data["name"]:
        target.name = data["name"]
    audit(db, actor, "USER_UPDATE", "user", target.id, f"{target.name}: {data}")
    db.commit()
    return {"id": target.id, "email": target.email, "name": target.name,
            "role": target_m.role, "is_active": target.is_active}


@company_router.delete("/users/{user_id}")
def deactivate_user(user_id: int, actor: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    """사용자 접근 해제 — 계정 비활성화 + 해당 기업 소속 제거."""
    target = db.get(User, user_id)
    target_m = _membership(db, user_id, actor.company_id) if actor.company_id else None
    if not target or not target_m:
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    if target_m.role == "OWNER" and actor.role != "OWNER":
        raise HTTPException(403, "OWNER는 OWNER만 해제할 수 있습니다.")
    if target.id == actor.id:
        raise HTTPException(400, "본인 계정은 해제할 수 없습니다.")
    db.delete(target_m)
    if target.company_id == actor.company_id:
        target.company_id = None
    if not db.query(Membership).filter(Membership.user_id == target.id).count():
        target.is_active = False
    audit(db, actor, "USER_DEACTIVATE", "user", target.id, target.name)
    db.commit()
    return {"ok": True}


# ----- 기업 사용자 초대 -----

@company_router.post("/invites")
def create_invite(body: InviteCreate, actor: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    if not actor.company_id:
        raise HTTPException(400, "소속 기업이 없습니다.")
    if body.role not in INVITABLE_ROLES:
        raise HTTPException(400, f"초대 가능한 권한: {', '.join(sorted(INVITABLE_ROLES))}")
    email = body.email.strip().lower()
    # 이미 소속된 사용자는 초대 불가
    existing = db.query(User).filter(User.email == email).first()
    if existing and _membership(db, existing.id, actor.company_id):
        raise HTTPException(409, "이미 해당 기업에 소속된 사용자입니다.")
    # 동일 이메일 대기 중 초대가 있으면 갱신
    db.query(CompanyInvite).filter(
        CompanyInvite.company_id == actor.company_id,
        CompanyInvite.email == email,
        CompanyInvite.status == "pending").delete()

    token = generate_token()
    inv = CompanyInvite(
        company_id=actor.company_id, email=email, role=body.role,
        token_hash=hash_token(token), invited_by=actor.name,
        expires_at=datetime.utcnow() + timedelta(days=INVITE_TTL_DAYS))
    db.add(inv)
    audit(db, actor, "INVITE_CREATE", "invite", inv.id or "", f"{email} → {body.role}")
    db.commit()
    # 이메일 발송 모듈 미연동 — 초대 토큰을 응답에 포함(연동 시 제거)
    return {"invite": invite_dict(inv), "invite_token": token,
            "note": "이메일 발송 모듈 미연동 상태로, 초대 토큰을 응답에 포함합니다."}


@company_router.get("/invites")
def list_invites(actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    if not actor.company_id:
        return []
    _expire_invites(db, actor.company_id)
    rows = db.query(CompanyInvite).filter(
        CompanyInvite.company_id == actor.company_id).order_by(
        CompanyInvite.created_at.desc()).limit(100).all()
    return [invite_dict(i) for i in rows]


@company_router.post("/invites/{invite_id}/cancel")
def cancel_invite(invite_id: int, actor: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    inv = db.get(CompanyInvite, invite_id)
    if not inv or inv.company_id != actor.company_id:
        raise HTTPException(404, "초대를 찾을 수 없습니다.")
    if inv.status != "pending":
        raise HTTPException(400, f"취소할 수 없는 상태입니다: {inv.status}")
    inv.status = "cancelled"
    audit(db, actor, "INVITE_CANCEL", "invite", inv.id, inv.email)
    db.commit()
    return {"ok": True}


@company_router.post("/invites/accept")
def accept_invite(body: InviteAccept, user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """초대 수락 — 초대 이메일과 로그인 계정이 일치해야 한다."""
    inv = db.query(CompanyInvite).filter(
        CompanyInvite.token_hash == hash_token(body.token.strip())).first()
    if not inv or inv.status != "pending":
        raise HTTPException(400, "유효하지 않은 초대입니다.")
    if inv.expires_at < datetime.utcnow():
        inv.status = "expired"
        db.commit()
        raise HTTPException(400, "만료된 초대입니다.")
    if inv.email != user.email:
        raise HTTPException(403, "초대된 이메일과 로그인 계정이 다릅니다.")
    if _membership(db, user.id, inv.company_id):
        inv.status = "accepted"
        db.commit()
        raise HTTPException(409, "이미 해당 기업에 소속되어 있습니다.")

    m = Membership(user_id=user.id, company_id=inv.company_id, role=inv.role)
    db.add(m)
    inv.status = "accepted"
    inv.accepted_by = user.email
    _activate_company(user, m)
    audit(db, user, "INVITE_ACCEPT", "invite", inv.id, f"{inv.email} → {inv.role}")
    db.commit()
    company = db.get(Company, inv.company_id)
    return {"company": company_dict(company), "role": inv.role}


def _expire_invites(db: Session, company_id: int):
    now = datetime.utcnow()
    db.query(CompanyInvite).filter(
        CompanyInvite.company_id == company_id,
        CompanyInvite.status == "pending",
        CompanyInvite.expires_at < now).update({"status": "expired"})
    db.flush()
