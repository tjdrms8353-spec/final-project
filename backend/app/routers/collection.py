"""외부 데이터 수집 상태·수동 실행 API (정식 전환 B 보완).

- 공통 외부 데이터는 플랫폼 공유 — 수집 스케줄 변경 API는 없다(운영 설정은 환경변수로만).
- 기업 관리자의 수동 실행은 내 기업 관련성 점수 갱신 목적이며, 기업당 1시간 1회로 제한한다.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, require_admin
from ..models import CollectionRun, MarketSeries, NewsItem, User
from ..services.collection_service import (
    collectors_status, manual_run_allowed, mark_manual_run, run_collection,
)

router = APIRouter(prefix="/api/collection", tags=["collection"])


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """수집기별 활성·스케줄·최신성 상태, 최근 수집 이력, 내 기업 연결 데이터 건수."""
    cid = user.company_id
    runs = (db.query(CollectionRun)
            .order_by(CollectionRun.started_at.desc()).limit(10).all())
    return {
        "collectors": collectors_status(db),
        "recent_runs": [
            {"collector": r.collector, "trigger": r.trigger, "status": r.status,
             "series_count": r.series_count, "news_count": r.news_count,
             "error": r.error, "started_at": r.started_at.isoformat(),
             "finished_at": r.finished_at.isoformat() if r.finished_at else None}
            for r in runs
        ],
        "company_data": {
            # 공통 외부 데이터는 1회 저장, 기업은 읽기만 한다
            "market_series": db.query(MarketSeries).filter(
                MarketSeries.company_id.is_(None),
                ~MarketSeries.source.like("(데모)%")).count(),
            "news_real": db.query(NewsItem).filter(
                NewsItem.company_id.is_(None), NewsItem.is_demo == False).count(),  # noqa: E712
        },
        "manual_run_cooldown_sec": manual_run_allowed(cid) if cid else 0,
    }


@router.post("/run")
def run(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """내 기업 대상 수동 수집 (ADMIN/OWNER, 기업당 1시간 1회 제한)."""
    if not user.company_id:
        raise HTTPException(400, "소속 기업이 없습니다.")
    wait = manual_run_allowed(user.company_id)
    if wait > 0:
        raise HTTPException(429, f"수동 수집은 기업당 1시간 1회로 제한됩니다. {wait // 60}분 후 재시도하세요.")
    mark_manual_run(user.company_id)
    return run_collection(db, company_id=user.company_id, trigger="manual")
