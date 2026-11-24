from datetime import date, datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Header, HTTPException, Path, Query, UploadFile
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db

from . import market, reports
from .analysis import company_records, related_news
from .analysis import run_analysis as execute_analysis
from .erp_import import TEMPLATE_CSV, LedgerFormatError, parse_ledger
from .industries import INDUSTRIES, get_template, template_dict
from .metrics import monthly_summary
from .models import (AnalysisFinding, AnalysisRun, AuditLog, BiUser, Company, CompanyMember, Decision, ErpRecord,
                     ErpUpload, FollowUpAction, MarketIndicator)
from .security import create_token, hash_password, read_token, verify_password
from .simulation import simulate

router = APIRouter(tags=["bi"])

ROLES = ("OWNER", "APPROVER", "ANALYST", "VIEWER")
WRITE_ROLES = ("OWNER", "APPROVER", "ANALYST")
DECIDE_ROLES = ("OWNER", "APPROVER")
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def audit(db: Session, company_id: int, user: BiUser, action: str, entity_type: str,
          entity_id: int | None = None, detail: dict | None = None) -> None:
    """Append one row to the company audit trail (committed with the caller's transaction)."""
    db.add(AuditLog(company_id=company_id, user_id=user.id, action=action, entity_type=entity_type,
                    entity_id=entity_id, detail=detail or {}, created_at=now()))


def bi_db():
    try:
        yield from get_db()
    except (SQLAlchemyError, RuntimeError, ValueError, OSError):
        raise HTTPException(status_code=503, detail="BI database unavailable") from None


Db = Annotated[Session, Depends(bi_db)]


def current_user(db: Db, authorization: Annotated[str | None, Header()] = None) -> BiUser:
    token = (authorization or "").removeprefix("Bearer ").strip()
    user_id = read_token(token) if token else None
    user = db.get(BiUser, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user


User = Annotated[BiUser, Depends(current_user)]


def membership(db: Session, company_id: int, user: BiUser, allowed: tuple[str, ...] = ROLES) -> tuple[Company, str]:
    company = db.get(Company, company_id)
    member = db.get(CompanyMember, {"company_id": company_id, "user_id": user.id})
    if company is None or member is None:
        raise HTTPException(status_code=404, detail="기업을 찾을 수 없거나 접근 권한이 없습니다.")
    if member.role not in allowed:
        raise HTTPException(status_code=403, detail=f"이 작업은 {', '.join(allowed)} 권한이 필요합니다.")
    return company, member.role


CompanyId = Annotated[int, Path(ge=1)]


# ---------- auth ----------
class RegisterIn(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


def user_out(user: BiUser) -> dict:
    return {"id": user.id, "email": user.email, "name": user.name}


@router.post("/auth/register", status_code=201)
def register(body: RegisterIn, db: Db):
    if db.scalar(select(BiUser).where(BiUser.email == body.email.lower())):
        raise HTTPException(status_code=409, detail="이미 가입된 이메일입니다.")
    user = BiUser(email=body.email.lower(), name=body.name.strip(), password_hash=hash_password(body.password), created_at=now())
    db.add(user)
    db.commit()
    return {"token": create_token(user.id), "user": user_out(user)}


@router.post("/auth/login")
def login(body: LoginIn, db: Db):
    user = db.scalar(select(BiUser).where(BiUser.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="이메일 또는 비밀번호가 올바르지 않습니다.")
    return {"token": create_token(user.id), "user": user_out(user)}


@router.get("/auth/me")
def me(user: User):
    return user_out(user)


# ---------- industries & companies ----------
@router.get("/industries")
def industries():
    return [template_dict(t) for t in INDUSTRIES.values()]


class CompanyIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str = "semiconductor"
    main_products: list[str] = Field(default_factory=list, max_length=20)
    interest_industries: list[str] = Field(default_factory=list, max_length=20)
    trade_countries: list[str] = Field(default_factory=list, max_length=30)
    interest_indicators: list[str] = Field(default_factory=list, max_length=20)
    annual_import_krw: float | None = Field(default=None, ge=0, le=1e13)


def company_out(company: Company, role: str) -> dict:
    return {
        "id": company.id, "name": company.name, "industry": company.industry,
        "industry_label": get_template(company.industry).label, "main_products": company.main_products,
        "interest_industries": company.interest_industries, "trade_countries": company.trade_countries,
        "interest_indicators": company.interest_indicators, "role": role,
        "annual_import_krw": company.annual_import_krw,
    }


def _clean(values: list[str]) -> list[str]:
    return [v.strip()[:100] for v in values if v and v.strip()]


@router.post("/companies", status_code=201)
def create_company(body: CompanyIn, db: Db, user: User):
    if body.industry not in INDUSTRIES:
        raise HTTPException(status_code=422, detail=f"지원 업종: {', '.join(INDUSTRIES)}")
    template = INDUSTRIES[body.industry]
    company = Company(
        name=body.name.strip(), industry=body.industry, main_products=_clean(body.main_products),
        interest_industries=_clean(body.interest_industries), trade_countries=_clean(body.trade_countries),
        interest_indicators=_clean(body.interest_indicators) or list(template.market_indicators),
        annual_import_krw=body.annual_import_krw,
        created_by=user.id, created_at=now(),
    )
    db.add(company)
    db.flush()
    db.add(CompanyMember(company_id=company.id, user_id=user.id, role="OWNER"))
    audit(db, company.id, user, "COMPANY_CREATED", "company", company.id,
          {"name": company.name, "industry": company.industry})
    db.commit()
    return company_out(company, "OWNER")


@router.get("/companies")
def list_companies(db: Db, user: User):
    rows = db.execute(select(Company, CompanyMember.role).join(CompanyMember, CompanyMember.company_id == Company.id)
                      .where(CompanyMember.user_id == user.id).order_by(Company.id)).all()
    return [company_out(c, r) for c, r in rows]


@router.get("/companies/{company_id}")
def get_company(company_id: CompanyId, db: Db, user: User):
    company, role = membership(db, company_id, user)
    return company_out(company, role)


@router.put("/companies/{company_id}")
def update_company(company_id: CompanyId, body: CompanyIn, db: Db, user: User):
    company, _ = membership(db, company_id, user, ("OWNER",))
    if body.industry not in INDUSTRIES:
        raise HTTPException(status_code=422, detail=f"지원 업종: {', '.join(INDUSTRIES)}")
    template = INDUSTRIES[body.industry]
    company.name = body.name.strip()
    company.industry = body.industry
    company.main_products = _clean(body.main_products)
    company.interest_industries = _clean(body.interest_industries)
    company.trade_countries = _clean(body.trade_countries)
    company.interest_indicators = _clean(body.interest_indicators) or list(template.market_indicators)
    company.annual_import_krw = body.annual_import_krw
    audit(db, company_id, user, "COMPANY_UPDATED", "company", company.id,
          {"name": company.name, "industry": company.industry})
    db.commit()
    return company_out(company, "OWNER")


class MemberIn(BaseModel):
    email: EmailStr
    role: Literal["OWNER", "APPROVER", "ANALYST", "VIEWER"]


@router.get("/companies/{company_id}/members")
def list_members(company_id: CompanyId, db: Db, user: User):
    membership(db, company_id, user)
    rows = db.execute(select(BiUser, CompanyMember.role).join(CompanyMember, CompanyMember.user_id == BiUser.id)
                      .where(CompanyMember.company_id == company_id).order_by(BiUser.id)).all()
    return [{**user_out(u), "role": r} for u, r in rows]


@router.put("/companies/{company_id}/members")
def upsert_member(company_id: CompanyId, body: MemberIn, db: Db, user: User):
    membership(db, company_id, user, ("OWNER",))
    target = db.scalar(select(BiUser).where(BiUser.email == body.email.lower()))
    if target is None:
        raise HTTPException(status_code=404, detail="가입된 사용자가 아닙니다. 먼저 회원가입이 필요합니다.")
    member = db.get(CompanyMember, {"company_id": company_id, "user_id": target.id})
    if member:
        member.role = body.role
    else:
        db.add(CompanyMember(company_id=company_id, user_id=target.id, role=body.role))
    audit(db, company_id, user, "MEMBER_UPDATED", "member", target.id,
          {"email": target.email, "name": target.name, "role": body.role})
    db.commit()
    return {**user_out(target), "role": body.role}


# ---------- ERP upload ----------
@router.get("/erp/template.csv", response_class=PlainTextResponse)
def erp_template():
    return PlainTextResponse(TEMPLATE_CSV, media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": "attachment; filename=dayribbon_erp_template.csv"})


@router.post("/companies/{company_id}/erp/upload", status_code=201)
async def upload_erp(company_id: CompanyId, db: Db, user: User, file: UploadFile = File(...)):
    membership(db, company_id, user, WRITE_ROLES)
    content = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="파일은 10MB 이하만 업로드할 수 있습니다.")
    try:
        parsed = parse_ledger(file.filename or "upload.csv", content)
    except LedgerFormatError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None
    if not parsed.rows:
        raise HTTPException(status_code=422, detail={"message": "유효한 행이 없습니다.", "errors": parsed.errors})
    upload = ErpUpload(company_id=company_id, file_name=(file.filename or "upload")[:255], row_count=len(parsed.rows),
                       rejected_count=parsed.rejected, uploaded_by=user.id, uploaded_at=now())
    db.add(upload)
    db.flush()
    db.add_all([ErpRecord(company_id=company_id, upload_id=upload.id, **row) for row in parsed.rows])
    audit(db, company_id, user, "ERP_UPLOAD", "erp_upload", upload.id,
          {"file_name": upload.file_name, "accepted": len(parsed.rows), "rejected": parsed.rejected})
    db.commit()
    return {"upload_id": upload.id, "accepted": len(parsed.rows), "rejected": parsed.rejected, "errors": parsed.errors}


@router.get("/companies/{company_id}/erp/uploads")
def list_uploads(company_id: CompanyId, db: Db, user: User):
    membership(db, company_id, user)
    rows = db.scalars(select(ErpUpload).where(ErpUpload.company_id == company_id).order_by(ErpUpload.id.desc())).all()
    return [{"id": u.id, "file_name": u.file_name, "row_count": u.row_count, "rejected_count": u.rejected_count,
             "uploaded_at": u.uploaded_at.isoformat()} for u in rows]


# ---------- market data ----------
class IndicatorIn(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    obs_date: date
    value: float
    source: str = Field(min_length=1, max_length=100)
    source_url: str = Field(default="", max_length=1000)


@router.post("/market/fx/collect")
def collect_fx(db: Db, user: User, days: Annotated[int, Query(ge=7, le=365)] = 120):
    try:
        result = market.collect_fx(db, days=days)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"환율 API 요청 실패: {type(exc).__name__}") from None
    db.commit()
    return result


@router.post("/market/macro/collect")
def collect_macro(db: Db, user: User, days: Annotated[int, Query(ge=30, le=365)] = 180):
    try:
        result = market.collect_macro(db, days=days)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"매크로 API 요청 실패: {type(exc).__name__}") from None
    db.commit()
    return result


@router.post("/market/indicators", status_code=201)
def add_indicator(body: IndicatorIn, db: Db, user: User):
    inserted = market.store_indicators(db, [body.model_dump()])
    db.commit()
    return {"inserted": inserted}


@router.get("/market/indicators")
def get_indicators(db: Db, user: User, code: Annotated[str, Query(max_length=30)] = "USD/KRW",
                   limit: Annotated[int, Query(ge=1, le=365)] = 120):
    series = market.indicator_series(db, code, limit)
    return {"code": code, "change_30d": market.change_over(series),
            "series": [{"date": s.obs_date.isoformat(), "value": s.value, "source": s.source} for s in series]}


# ---------- dashboard ----------
@router.get("/companies/{company_id}/dashboard")
def dashboard(company_id: CompanyId, db: Db, user: User):
    company, role = membership(db, company_id, user)
    template = get_template(company.industry)
    monthly = monthly_summary(company_records(db, company_id))
    latest = monthly[-1] if monthly else None
    kpis = [{**k.__dict__, "value": latest.get(k.code) if latest else None,
             "previous": monthly[-2].get(k.code) if len(monthly) > 1 else None} for k in template.kpis]
    indicators = {}
    for code in company.interest_indicators or template.market_indicators:
        series = market.indicator_series(db, code, 120)
        indicators[code] = {"change_30d": market.change_over(series),
                            "series": [{"date": s.obs_date.isoformat(), "value": s.value} for s in series]}
    news = related_news(db, list(company.main_products) + list(template.news_keywords) + list(company.interest_industries))
    return {"company": company_out(company, role), "template": template_dict(template), "period": latest["period"] if latest else None,
            "kpis": kpis, "monthly": monthly, "indicators": indicators, "news": news}


# ---------- analysis ----------
def finding_out(f: AnalysisFinding) -> dict:
    return {k: getattr(f, k) for k in ("id", "run_id", "kind", "severity", "title", "facts", "inference", "evidence",
                                       "uncertainty", "review_points", "recommendation", "status")}


def run_out(run: AnalysisRun, findings: list[AnalysisFinding]) -> dict:
    return {"id": run.id, "period": run.period, "narrative": run.narrative, "narrative_source": run.narrative_source,
            "metrics": run.metrics, "created_at": run.created_at.isoformat(), "findings": [finding_out(f) for f in findings]}


@router.post("/companies/{company_id}/analyses", status_code=201)
def create_analysis(company_id: CompanyId, db: Db, user: User):
    company, _ = membership(db, company_id, user, WRITE_ROLES)
    if not db.scalar(select(ErpRecord.id).where(ErpRecord.company_id == company_id).limit(1)):
        raise HTTPException(status_code=422, detail="분석할 ERP 데이터가 없습니다. 먼저 CSV/Excel을 업로드해 주세요.")
    run = execute_analysis(db, company, user.id)
    findings_count = len(db.scalars(select(AnalysisFinding.id).where(AnalysisFinding.run_id == run.id)).all())
    audit(db, company_id, user, "ANALYSIS_RUN", "analysis_run", run.id,
          {"period": run.period, "findings": findings_count, "narrative_source": run.narrative_source})
    db.commit()
    return run_out(run, db.scalars(select(AnalysisFinding).where(AnalysisFinding.run_id == run.id)).all())


@router.get("/companies/{company_id}/analyses")
def list_analyses(company_id: CompanyId, db: Db, user: User):
    membership(db, company_id, user)
    runs = db.scalars(select(AnalysisRun).where(AnalysisRun.company_id == company_id).order_by(AnalysisRun.id.desc()).limit(20)).all()
    return [{"id": r.id, "period": r.period, "created_at": r.created_at.isoformat(), "narrative_source": r.narrative_source} for r in runs]


@router.get("/companies/{company_id}/analyses/{run_id}")
def get_analysis(company_id: CompanyId, run_id: Annotated[int, Path(ge=1)], db: Db, user: User):
    membership(db, company_id, user)
    run = db.get(AnalysisRun, run_id)
    if run is None or run.company_id != company_id:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    return run_out(run, db.scalars(select(AnalysisFinding).where(AnalysisFinding.run_id == run.id)).all())


# ---------- decisions ----------
class DecisionIn(BaseModel):
    status: Literal["APPROVED", "ON_HOLD", "REJECTED"]
    reason: str = Field(min_length=1, max_length=2000)
    assignee_id: int | None = None
    follow_up: str | None = Field(default=None, max_length=300)
    due_date: date | None = None


def _check_assignee(db: Session, company_id: int, assignee_id: int | None):
    if assignee_id is not None and db.get(CompanyMember, {"company_id": company_id, "user_id": assignee_id}) is None:
        raise HTTPException(status_code=422, detail="담당자는 같은 기업의 구성원이어야 합니다.")


@router.post("/companies/{company_id}/findings/{finding_id}/decisions", status_code=201)
def decide(company_id: CompanyId, finding_id: Annotated[int, Path(ge=1)], body: DecisionIn, db: Db, user: User):
    membership(db, company_id, user, DECIDE_ROLES)
    finding = db.get(AnalysisFinding, finding_id)
    if finding is None or finding.company_id != company_id:
        raise HTTPException(status_code=404, detail="분석 항목을 찾을 수 없습니다.")
    _check_assignee(db, company_id, body.assignee_id)
    decision = Decision(finding_id=finding_id, company_id=company_id, status=body.status, reason=body.reason.strip(),
                        assignee_id=body.assignee_id, decided_by=user.id, decided_at=now())
    db.add(decision)
    finding.status = body.status
    db.flush()
    action = None
    if body.follow_up and body.follow_up.strip():
        action = FollowUpAction(decision_id=decision.id, company_id=company_id, title=body.follow_up.strip(),
                                assignee_id=body.assignee_id, due_date=body.due_date, status="OPEN", updated_at=now())
        db.add(action)
    audit(db, company_id, user, "DECISION", "finding", finding_id,
          {"status": body.status, "reason": body.reason.strip()[:300], "assignee_id": body.assignee_id,
           "follow_up": (body.follow_up or "").strip()[:300] or None})
    db.commit()
    return {"id": decision.id, "status": decision.status, "finding_status": finding.status,
            "follow_up_id": action.id if action else None}


@router.get("/companies/{company_id}/decisions")
def list_decisions(company_id: CompanyId, db: Db, user: User):
    membership(db, company_id, user)
    rows = db.execute(select(Decision, AnalysisFinding.title, BiUser.name)
                      .join(AnalysisFinding, AnalysisFinding.id == Decision.finding_id)
                      .join(BiUser, BiUser.id == Decision.decided_by)
                      .where(Decision.company_id == company_id).order_by(Decision.id.desc())).all()
    names = dict(db.execute(select(BiUser.id, BiUser.name)).all())
    return [{"id": d.id, "finding_id": d.finding_id, "finding_title": title, "status": d.status, "reason": d.reason,
             "decided_by": by, "assignee": names.get(d.assignee_id), "decided_at": d.decided_at.isoformat()}
            for d, title, by in rows]


class ActionUpdate(BaseModel):
    status: Literal["OPEN", "IN_PROGRESS", "DONE"]


@router.get("/companies/{company_id}/actions")
def list_actions(company_id: CompanyId, db: Db, user: User):
    membership(db, company_id, user)
    names = dict(db.execute(select(BiUser.id, BiUser.name)).all())
    rows = db.scalars(select(FollowUpAction).where(FollowUpAction.company_id == company_id).order_by(FollowUpAction.id.desc())).all()
    return [{"id": a.id, "decision_id": a.decision_id, "title": a.title, "assignee": names.get(a.assignee_id),
             "due_date": a.due_date.isoformat() if a.due_date else None, "status": a.status} for a in rows]


@router.patch("/companies/{company_id}/actions/{action_id}")
def update_action(company_id: CompanyId, action_id: Annotated[int, Path(ge=1)], body: ActionUpdate, db: Db, user: User):
    membership(db, company_id, user, WRITE_ROLES)
    action = db.get(FollowUpAction, action_id)
    if action is None or action.company_id != company_id:
        raise HTTPException(status_code=404, detail="후속 조치를 찾을 수 없습니다.")
    previous = action.status
    action.status, action.updated_at = body.status, now()
    audit(db, company_id, user, "ACTION_UPDATE", "follow_up_action", action.id,
          {"title": action.title, "from": previous, "to": body.status})
    db.commit()
    return {"id": action.id, "status": action.status}


# ---------- simulation (phase 2) ----------
class SimulationIn(BaseModel):
    fx_pct: float = Field(default=0, ge=-50, le=50)
    purchase_price_pct: float = Field(default=0, ge=-50, le=100)
    sales_pct: float = Field(default=0, ge=-90, le=100)
    volume_pct: float = Field(default=0, ge=-90, le=100)


@router.post("/companies/{company_id}/simulate")
def run_simulation(company_id: CompanyId, body: SimulationIn, db: Db, user: User):
    membership(db, company_id, user)
    monthly = monthly_summary(company_records(db, company_id))
    if not monthly:
        raise HTTPException(status_code=422, detail="시뮬레이션 기준이 될 ERP 데이터가 없습니다.")
    audit(db, company_id, user, "SIMULATION_RUN", "simulation", None, dict(body.model_dump()))
    db.commit()
    return simulate(monthly[-1], **body.model_dump())


# ---------- reports & audit trail ----------
@router.get("/companies/{company_id}/reports")
def get_report(company_id: CompanyId, db: Db, user: User,
               kind: Literal["weekly", "monthly"] = "monthly",
               month: Annotated[str | None, Query(max_length=7)] = None,
               anchor: date | None = None):
    company, _ = membership(db, company_id, user)
    try:
        if kind == "monthly":
            if month:
                year, mon = (int(part) for part in month.split("-"))
                if not 1 <= mon <= 12:
                    raise ValueError
                target = date(year, mon, 1)
            else:
                target = reports.today_kst().replace(day=1)
        else:
            target = anchor or reports.today_kst()
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="기간 형식이 올바르지 않습니다. (month=YYYY-MM, anchor=YYYY-MM-DD)") from None
    report = reports.build_report(db, company, kind, target, user)
    audit(db, company_id, user, "REPORT_GENERATED", "report", None, {"kind": kind, "period": report["period"]})
    db.commit()
    return report


@router.get("/companies/{company_id}/audit-logs")
def list_audit_logs(company_id: CompanyId, db: Db, user: User,
                    action: Annotated[str | None, Query(max_length=30)] = None,
                    limit: Annotated[int, Query(ge=1, le=200)] = 50,
                    offset: Annotated[int, Query(ge=0)] = 0):
    membership(db, company_id, user)
    stmt = select(AuditLog).where(AuditLog.company_id == company_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(AuditLog.id.desc()).limit(limit).offset(offset)).all()
    names = dict(db.execute(select(BiUser.id, BiUser.name).where(
        BiUser.id.in_({r.user_id for r in rows if r.user_id} or {0}))).all())
    return {"total": total, "items": [{"id": r.id, "action": r.action, "entity_type": r.entity_type,
                                       "entity_id": r.entity_id, "detail": r.detail,
                                       "user": names.get(r.user_id), "created_at": r.created_at.isoformat()}
                                      for r in rows]}
