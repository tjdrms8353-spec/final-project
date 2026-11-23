from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.db.session import get_db
from .repository import collection_gaps, find_news, search_news
from .schemas import CoverageResponse, SampleNewsResponse, NewsListResponse, StoredNewsItem
from .service import get_sample_news, get_status

router = APIRouter(tags=["news"])

@router.get("/status")
def status():
    return get_status()


@router.get(
    "/sample", response_model=SampleNewsResponse,
    summary="화면 연동용 가상 뉴스 목록",
    description=(
        "외부 수집·DB 접속 없이 가상 기사를 반환합니다. "
        "발행 시각 내림차순이며 limit은 1~100(기본 20)입니다. "
        "total은 limit 적용 전 개수입니다. 실제 기사 조회·분석 API와 구분하세요."
    ),
)
def read_sample_news(
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SampleNewsResponse:
    """Return fictional sample news without network or database access."""
    return get_sample_news(limit)


def news_db():
    try:
        yield from get_db()
    except (SQLAlchemyError, RuntimeError, ValueError, OSError):
        raise HTTPException(status_code=503, detail="News database unavailable") from None


@router.get("", response_model=NewsListResponse, summary="저장된 뉴스 목록",
            description="발행 시각(없으면 관측 시각) 최신순. 자동 실시간 수집을 의미하지 않습니다.")
def read_news(
    db: Annotated[Session, Depends(news_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: Annotated[str | None, Query(max_length=200)] = None,
    source: Annotated[str | None, Query(max_length=200)] = None,
) -> NewsListResponse:
    return search_news(db, limit=limit, offset=offset, q=q, source=source)


@router.get("/coverage", response_model=CoverageResponse, summary="출처별 수집 공백",
            description="최근 hours시간 동안 기사가 누락됐을 수 있는 구간. 순위·추세 계산에서 제외할 때 사용합니다.")
def read_coverage(
    db: Annotated[Session, Depends(news_db)],
    hours: Annotated[int, Query(ge=1, le=720)] = 24,
    feed: Annotated[str | None, Query(max_length=50)] = None,
) -> CoverageResponse:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=hours)
    return CoverageResponse(since=since, gaps=collection_gaps(db, since=since, now=now, feed=feed))


@router.get("/{article_id}", response_model=StoredNewsItem, summary="저장된 뉴스 상세")
def read_news_detail(
    article_id: Annotated[str, Path(pattern="^[0-9a-f]{64}$")],
    db: Annotated[Session, Depends(news_db)],
) -> StoredNewsItem:
    item = find_news(db, article_id)
    if item is None:
        raise HTTPException(status_code=404, detail="News article not found")
    return item
