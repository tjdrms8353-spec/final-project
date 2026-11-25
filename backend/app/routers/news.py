"""뉴스 및 산업 동향 — 기업 관련성 기반 선별 제공"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import NewsItem, User

router = APIRouter(prefix="/api/news", tags=["news"])

CATEGORIES = ["반도체", "정책", "거시경제", "공급망", "환율", "산업동향"]


def news_dict(n: NewsItem, detail: bool = False) -> dict:
    d = {
        "id": n.id, "title": n.title, "category": n.category,
        "sentiment": n.sentiment, "relevance_score": n.relevance_score,
        "importance": n.importance, "source": n.source,
        "summary": n.summary,
        "impact_on_company": n.impact_on_company, "why_relevant": n.why_relevant,
        "published_at": n.published_at.isoformat() if n.published_at else "",
        "is_demo": n.is_demo,
    }
    if detail:
        d["full_summary"] = n.summary
    return d


@router.get("")
def list_news(
    category: str | None = None,
    sentiment: str | None = None,
    importance: str | None = None,
    min_relevance: float = 0,
    days: int | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(NewsItem).filter(NewsItem.company_id == user.company_id)
    if category:
        q = q.filter(NewsItem.category == category)
    if sentiment:
        q = q.filter(NewsItem.sentiment == sentiment)
    if importance:
        q = q.filter(NewsItem.importance == importance)
    if min_relevance:
        q = q.filter(NewsItem.relevance_score >= min_relevance)
    if days:
        from datetime import datetime, timedelta
        q = q.filter(NewsItem.published_at >= datetime.utcnow() - timedelta(days=days))
    total = q.count()
    rows = q.order_by(NewsItem.published_at.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": [news_dict(n) for n in rows], "categories": CATEGORIES}


@router.get("/{news_id}")
def get_news(news_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    n = db.get(NewsItem, news_id)
    if not n or n.company_id != user.company_id:
        from fastapi import HTTPException
        raise HTTPException(404, "뉴스를 찾을 수 없습니다.")
    return news_dict(n, detail=True)
