"""경영 KPI API (정식 전환 C).

모든 수치는 services/kpi_service의 Python·Decimal 로직으로 계산되며,
데이터 부족·계산 불가는 0 대신 status로 명시한다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..services.kpi_service import compute_kpi_report
from ..services.risk_service import assess_risks

router = APIRouter(prefix="/api/kpi", tags=["kpi"])


def _cid(user: User) -> int:
    if not user.company_id:
        raise HTTPException(400, "소속 기업이 없습니다.")
    return user.company_id


@router.get("/summary")
def kpi_summary(user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    """최신 월 기준 KPI 리포트 — 계산식·기준·사용데이터·부족 여부 포함."""
    return compute_kpi_report(db, _cid(user))


@router.get("/risk")
def risk_summary(user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """기업 맞춤 위험 평가 — 수출입 구조·프로필 반영, 데이터 부족은 판단 보류."""
    return assess_risks(db, _cid(user))
