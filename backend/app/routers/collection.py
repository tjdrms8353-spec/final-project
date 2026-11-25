"""외부 데이터 수집 상태·수동 실행 API (정식 전환 B)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import MarketSeries, NewsItem, User
from ..services.collection_service import (
    LAST_RUN, collectors_status, run_collection,
)

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """수집기 활성 상태·마지막 실행·내 기업의 수집 데이터 건수."""
    cid = user.company_id
    return {
        "collectors": collectors_status(),
        "last_run": LAST_RUN,
        "company_data": {
            "market_series": db.query(MarketSeries).filter(
                MarketSeries.company_id == cid,
                ~MarketSeries.source.like("(데모)%")).count(),
            "news_real": db.query(NewsItem).filter(
                NewsItem.company_id == cid, NewsItem.is_demo == False).count(),  # noqa: E712
        } if cid else None,
    }


@router.post("/run")
def run(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """내 기업 대상 즉시 수집 실행 (ADMIN/OWNER 전용)."""
    if not user.company_id:
        raise HTTPException(400, "소속 기업이 없습니다.")
    return run_collection(db, company_id=user.company_id)
