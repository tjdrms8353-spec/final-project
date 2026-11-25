"""뉴스 및 산업 동향 — 기업 관련성 기반 선별 제공.

공통 수집 뉴스(company_id=NULL)는 모든 기업이 공유하고,
기업별 관련성은 company_news_scores로 병합해 제공한다.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import CompanyNewsScore, NewsItem, User
from ..utils import company_or_common

router = APIRouter(prefix="/api/news", tags=["news"])

CATEGORIES = ["반도체", "정책", "거시경제", "공급망", "환율", "금리", "원자재", "수출입", "산업동향"]


def news_dict(n: NewsItem, detail: bool = False,
              score: CompanyNewsScore | None = None) -> dict:
    d = {
        "id": n.id, "title": n.title, "category": n.category,
        "sentiment": n.sentiment,
        # 기업별 점수가 있으면 우선 (공통 뉴스), 없으면 뉴스 자체 값(기업 전용·데모)
        "relevance_score": score.relevance_score if score else n.relevance_score,
        "importance": score.importance if score else n.importance,
        "source": n.source, "link": n.link,
        "summary": n.summary,
        "impact_on_company": score.impact_on_company if score else n.impact_on_company,
        "why_relevant": score.why_relevant if score else n.why_relevant,
        "published_at": n.published_at.isoformat() if n.published_at else "",
        "is_demo": n.is_demo,
    }
    if detail:
        d["full_summary"] = n.summary
    return d


def _score_map(db: Session, company_id: int, news_ids: list[int]) -> dict[int, CompanyNewsScore]:
    if not news_ids:
        return {}
    return {s.news_item_id: s for s in db.query(CompanyNewsScore).filter(
        CompanyNewsScore.company_id == company_id,
        CompanyNewsScore.news_item_id.in_(news_ids)).all()}


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
    cid = user.company_id
    relevance = func.coalesce(CompanyNewsScore.relevance_score, NewsItem.relevance_score)
    imp = func.coalesce(CompanyNewsScore.importance, NewsItem.importance)

    q = (
        db.query(NewsItem)
        .outerjoin(CompanyNewsScore,
                   (CompanyNewsScore.news_item_id == NewsItem.id)
                   & (CompanyNewsScore.company_id == cid))
        .filter(company_or_common(NewsItem.company_id, cid))
    )
    if category:
        q = q.filter(NewsItem.category == category)
    if sentiment:
        q = q.filter(NewsItem.sentiment == sentiment)
    if importance:
        q = q.filter(imp == importance)
    if min_relevance:
        q = q.filter(relevance >= min_relevance)
    if days:
        from datetime import datetime, timedelta
        q = q.filter(NewsItem.published_at >= datetime.utcnow() - timedelta(days=days))
    total = q.count()
    rows = q.order_by(NewsItem.published_at.desc()).offset(offset).limit(limit).all()
    scores = _score_map(db, cid, [n.id for n in rows])
    return {"total": total,
            "items": [news_dict(n, score=scores.get(n.id)) for n in rows],
            "categories": CATEGORIES}


@router.get("/{news_id}")
def get_news(news_id: int, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    n = db.get(NewsItem, news_id)
    if not n or (n.company_id is not None and n.company_id != user.company_id):
        raise HTTPException(404, "뉴스를 찾을 수 없습니다.")
    score = db.query(CompanyNewsScore).filter_by(
        company_id=user.company_id, news_item_id=news_id).first()
    return news_dict(n, detail=True, score=score)
