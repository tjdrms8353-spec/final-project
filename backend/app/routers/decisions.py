"""의사결정 및 후속 조치 관리 — 최종 결정은 항상 사람(관리자)이 수행"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_admin, require_write
from ..models import AnalysisResult, Decision, FollowUp, User
from ..schemas import DecisionCreate, DecisionUpdate, FollowUpCreate, FollowUpUpdate

router = APIRouter(prefix="/api", tags=["decisions"])

DECISION_STATUSES = {"검토 대기", "검토 중", "수용", "보류", "미수용", "처리 완료"}
DECISIONS = {"수용", "보류", "미수용"}
FU_STATUSES = {"등록", "진행 중", "완료"}


def d_dict(d: Decision, db: Session) -> dict:
    a = db.get(AnalysisResult, d.analysis_result_id) if d.analysis_result_id else None
    fus = db.query(FollowUp).filter(FollowUp.decision_id == d.id).all()
    return {
        "id": d.id, "analysis_result_id": d.analysis_result_id,
        "analysis_title": a.title if a else "(분석 미연결)",
        "analysis_type": a.analysis_type if a else "",
        "status": d.status, "decision": d.decision, "reason": d.reason,
        "assignee": d.assignee, "due_date": d.due_date,
        "created_by": d.created_by,
        "created_at": d.created_at.isoformat() if d.created_at else "",
        "updated_at": d.updated_at.isoformat() if d.updated_at else "",
        "follow_ups": [{
            "id": f.id, "title": f.title, "status": f.status,
            "assignee": f.assignee, "due_date": f.due_date,
            "created_at": f.created_at.isoformat() if f.created_at else "",
        } for f in fus],
    }


@router.get("/decisions")
def list_decisions(status: str | None = None, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    q = db.query(Decision).filter(Decision.company_id == user.company_id)
    if status:
        q = q.filter(Decision.status == status)
    rows = q.order_by(Decision.updated_at.desc()).limit(100).all()
    return {"items": [d_dict(d, db) for d in rows],
            "statuses": sorted(DECISION_STATUSES), "decisions": sorted(DECISIONS)}


@router.post("/decisions")
def create_decision(body: DecisionCreate, user: User = Depends(require_admin),
                    db: Session = Depends(get_db)):
    if body.analysis_result_id:
        a = db.get(AnalysisResult, body.analysis_result_id)
        if not a or a.company_id != user.company_id:
            raise HTTPException(404, "연결할 분석 결과를 찾을 수 없습니다.")
    if body.status not in DECISION_STATUSES:
        raise HTTPException(400, "올바르지 않은 상태입니다.")
    if body.decision and body.decision not in DECISIONS:
        raise HTTPException(400, "결정은 수용/보류/미수용 중 하나여야 합니다.")
    d = Decision(company_id=user.company_id, **body.model_dump(),
                 created_by=user.name)
    db.add(d)
    db.flush()
    # 연결된 분석 결과 상태도 함께 갱신
    if d.analysis_result_id:
        a = db.get(AnalysisResult, d.analysis_result_id)
        if a and d.decision:
            a.status = {"수용": "수용", "보류": "보류", "미수용": "미수용"}[d.decision]
            a.reviewed_by = user.name
            from datetime import datetime
            a.reviewed_at = datetime.utcnow()
    audit(db, user, "DECISION_CREATE", "decision", d.id,
          f"{d.status}/{d.decision} — {d.reason[:100]}")
    db.commit()
    return d_dict(d, db)


@router.patch("/decisions/{decision_id}")
def update_decision(decision_id: int, body: DecisionUpdate,
                    user: User = Depends(require_admin), db: Session = Depends(get_db)):
    d = db.get(Decision, decision_id)
    if not d or d.company_id != user.company_id:
        raise HTTPException(404, "의사결정을 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in DECISION_STATUSES:
        raise HTTPException(400, "올바르지 않은 상태입니다.")
    if "decision" in data and data["decision"] and data["decision"] not in DECISIONS:
        raise HTTPException(400, "결정은 수용/보류/미수용 중 하나여야 합니다.")
    for k, v in data.items():
        setattr(d, k, v)
    audit(db, user, "DECISION_UPDATE", "decision", d.id, str(data))
    db.commit()
    return d_dict(d, db)


@router.post("/follow-ups")
def create_followup(body: FollowUpCreate, user: User = Depends(require_write),
                    db: Session = Depends(get_db)):
    f = FollowUp(company_id=user.company_id, title=body.title,
                 decision_id=body.decision_id, assignee=body.assignee,
                 due_date=body.due_date, created_by=user.name)
    db.add(f)
    audit(db, user, "FOLLOWUP_CREATE", "follow_up", f.id, body.title)
    db.commit()
    db.refresh(f)
    return {"id": f.id, "title": f.title, "status": f.status}


@router.patch("/follow-ups/{fu_id}")
def update_followup(fu_id: int, body: FollowUpUpdate,
                    user: User = Depends(require_write), db: Session = Depends(get_db)):
    f = db.get(FollowUp, fu_id)
    if not f or f.company_id != user.company_id:
        raise HTTPException(404, "후속 조치를 찾을 수 없습니다.")
    data = body.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in FU_STATUSES:
        raise HTTPException(400, "올바르지 않은 상태입니다.")
    for k, v in data.items():
        setattr(f, k, v)
    audit(db, user, "FOLLOWUP_UPDATE", "follow_up", f.id, str(data))
    db.commit()
    return {"id": f.id, "title": f.title, "status": f.status}
