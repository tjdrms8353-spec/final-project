"""AI 경영 분석 — 규칙 기반 데모 분석 결과 조회/실행/검토"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_admin, require_write
from ..models import AnalysisResult, User
from ..schemas import AnalysisReview
from ..services.analysis_engine import run_pipeline

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

TYPE_LABEL = {"growth": "미래 성장 가능성", "direction": "사업 방향성", "risk": "위험 요소 관리"}


def a_dict(a: AnalysisResult) -> dict:
    return {
        "id": a.id, "analysis_type": a.analysis_type,
        "analysis_type_label": TYPE_LABEL.get(a.analysis_type, a.analysis_type),
        "title": a.title, "summary": a.summary, "details": a.details,
        "data_sources": a.data_sources, "basis_date": a.basis_date,
        "impact": a.impact, "uncertainty": a.uncertainty, "suggestions": a.suggestions,
        "engine": a.engine, "engine_label": "규칙 기반 데모 분석",
        "status": a.status, "trigger": a.trigger,
        "created_at": a.created_at.isoformat() if a.created_at else "",
        "reviewed_by": a.reviewed_by,
        "reviewed_at": a.reviewed_at.isoformat() if a.reviewed_at else None,
    }


@router.get("")
def list_analyses(analysis_type: str | None = None,
                  user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    q = db.query(AnalysisResult).filter(AnalysisResult.company_id == user.company_id)
    if analysis_type:
        q = q.filter(AnalysisResult.analysis_type == analysis_type)
    rows = q.order_by(AnalysisResult.created_at.desc()).limit(50).all()
    return {"items": [a_dict(a) for a in rows], "types": TYPE_LABEL}


@router.get("/{analysis_id}")
def get_analysis(analysis_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    a = db.get(AnalysisResult, analysis_id)
    if not a or a.company_id != user.company_id:
        raise HTTPException(404, "분석 결과를 찾을 수 없습니다.")
    return a_dict(a)


@router.post("/run")
def run_analysis(user: User = Depends(require_write), db: Session = Depends(get_db)):
    """수동 분석 실행 — 규칙 기반 데모 엔진."""
    result = run_pipeline(db, user.company_id, trigger="manual")
    audit(db, user, "ANALYSIS_RUN", "analysis", "",
          f"수동 분석 실행: 분석 {result['new_analyses']}건, 알림 {result['new_alerts']}건")
    db.commit()
    return result


@router.patch("/{analysis_id}/review")
def review_analysis(analysis_id: int, body: AnalysisReview,
                    user: User = Depends(require_admin), db: Session = Depends(get_db)):
    a = db.get(AnalysisResult, analysis_id)
    if not a or a.company_id != user.company_id:
        raise HTTPException(404, "분석 결과를 찾을 수 없습니다.")
    valid = {"검토 대기", "검토 중", "수용", "보류", "미수용", "처리 완료"}
    if body.status not in valid:
        raise HTTPException(400, f"올바르지 않은 상태입니다: {body.status}")
    a.status = body.status
    a.reviewed_by = user.name
    from datetime import datetime
    a.reviewed_at = datetime.utcnow()
    audit(db, user, "ANALYSIS_REVIEW", "analysis_result", a.id,
          f"상태 → {body.status} {body.note}")
    db.commit()
    return a_dict(a)
