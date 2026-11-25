from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_admin, require_write
from ..models import Company, User
from ..schemas import CompanyUpdate, UserUpdate
from ..utils import fmt_krw

company_router = APIRouter(prefix="/api", tags=["company"])


def company_dict(c: Company) -> dict:
    return {
        "id": c.id, "name": c.name, "industry": c.industry, "size": c.size,
        "products": c.products, "key_customers": c.key_customers,
        "export_countries": c.export_countries, "import_countries": c.import_countries,
        "raw_materials": c.raw_materials, "export_import_ratio": c.export_import_ratio,
        "annual_revenue": c.annual_revenue, "annual_raw_material_cost": c.annual_raw_material_cost,
        "fx_settlement_ratio": c.fx_settlement_ratio,
        "interest_areas": c.interest_areas, "risk_concerns": c.risk_concerns,
        "annual_revenue_fmt": fmt_krw(c.annual_revenue),
        "annual_raw_material_cost_fmt": fmt_krw(c.annual_raw_material_cost),
    }


@company_router.get("/company")
def get_company(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return company_dict(user.company)


@company_router.put("/company")
def update_company(body: CompanyUpdate, user: User = Depends(require_write),
                   db: Session = Depends(get_db)):
    c = user.company
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(c, k, v)
    audit(db, user, "COMPANY_UPDATE", "company", c.id, f"수정 항목: {', '.join(data.keys())}")
    db.commit()
    return company_dict(c)


@company_router.get("/users")
def list_users(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.company_id == user.company_id).all()
    return [{"id": u.id, "email": u.email, "name": u.name, "role": u.role,
             "is_active": u.is_active} for u in users]


@company_router.put("/users/{user_id}")
def update_user(user_id: int, body: UserUpdate,
                actor: User = Depends(require_admin), db: Session = Depends(get_db)):
    target = db.get(User, user_id)
    if not target or target.company_id != actor.company_id:
        from fastapi import HTTPException
        raise HTTPException(404, "사용자를 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if "role" in data and data["role"] not in ("OWNER", "ADMIN", "MEMBER", "VIEWER"):
        from fastapi import HTTPException
        raise HTTPException(400, "올바르지 않은 권한 값입니다.")
    for k, v in data.items():
        setattr(target, k, v)
    audit(db, actor, "USER_UPDATE", "user", target.id, f"{target.name}: {data}")
    db.commit()
    return {"id": target.id, "email": target.email, "name": target.name,
            "role": target.role, "is_active": target.is_active}
