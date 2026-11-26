"""레거시 news_articles → news_items 일회성 이관 스크립트.

같은 dayribbon DB에 남아있던 이전 프로젝트의 뉴스 수집 데이터를
우리 공통 뉴스 저장소(news_items, company_id=NULL)로 이관한다.

- url → link (중복 방지의 기준 컬럼)
- title/summary/source/published_at 그대로 매핑
- category/sentiment는 기존 classify_news()로 분류
- is_demo=False — 실제 수집 데이터로 표기
- 이미 있는 link는 건너뜀 (재실행 안전)

실행: backend/ 디렉터리에서
    C:/venvs/dayribbon/Scripts/python.exe import_legacy_news.py
"""
from sqlalchemy import text

from app.database import SessionLocal
from app.models import NewsItem
from app.services.collection_service import classify_news


def main() -> None:
    db = SessionLocal()
    try:
        rows = db.execute(
            text("SELECT url, title, source, summary, published_at "
                 "FROM news_articles WHERE url IS NOT NULL AND url != ''")
        ).fetchall()
        existing = {r[0] for r in db.execute(
            text("SELECT link FROM news_items")).fetchall()}

        inserted = skipped = 0
        batch = []
        for url, title, source, summary, published_at in rows:
            url = (url or "")[:500]
            if not url or url in existing:
                skipped += 1
                continue
            title = (title or "")[:500]
            summary = summary or ""
            cat, sent = classify_news(title, summary)
            batch.append(NewsItem(
                company_id=None,
                title=title or "(제목 없음)",
                summary=summary,
                source=(source or "레거시 이관")[:200],
                link=url,
                category=cat,
                sentiment=sent,
                published_at=published_at,
                is_demo=False,
            ))
            existing.add(url)
            inserted += 1
            if len(batch) >= 500:
                db.add_all(batch)
                db.commit()
                batch.clear()
        if batch:
            db.add_all(batch)
            db.commit()
        print(f"이관 완료 - 총 {len(rows)}건 중 신규 {inserted}건, 중복/무효 {skipped}건")
    finally:
        db.close()


if __name__ == "__main__":
    main()
