"""Translate stored foreign articles (title + summary) into Korean with DeepL.

Run from the project root with backend on PYTHONPATH:
    python -m pipelines.jobs.translate_news            # dry run: count pending, no API call
    python -m pipelines.jobs.translate_news --execute  # one DeepL request, store results
"""
import argparse
import json
from datetime import datetime, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_engine
from app.features.trends.models import NewsArticle, NewsTranslation
from app.features.trends.translation import MAX_TEXTS, TranslationError, translate

FOREIGN_SOURCES = ("BBC News",)
LANG = "ko"
PROVIDER = "deepl"
BATCH = MAX_TEXTS // 2  # title + summary per article


def pending(db: Session, limit: int = BATCH) -> list[NewsArticle]:
    """Untranslated articles, plus ones whose summary arrived after translation."""
    query = select(NewsArticle).outerjoin(NewsTranslation, and_(
        NewsTranslation.url_hash == NewsArticle.url_hash, NewsTranslation.lang == LANG,
    )).where(NewsArticle.source.in_(FOREIGN_SOURCES), or_(
        NewsTranslation.url_hash.is_(None),
        and_(NewsTranslation.summary == "", NewsArticle.summary != ""),
    )).order_by(NewsArticle.sort_at.desc()).limit(limit)
    return list(db.scalars(query))


def run_translation(engine, *, api_key: str, limit: int = BATCH, client=None) -> dict:
    if not 1 <= limit <= BATCH:
        raise ValueError(f"limit must be between 1 and {BATCH}")
    if not api_key:
        return {"status": "skipped", "error_code": "missing_api_key", "translated": 0}
    try:
        # Read, then call DeepL with no open transaction, then write in a new one.
        with Session(engine) as db:
            articles = [(a.url_hash, a.title, a.summary) for a in pending(db, limit)]
        if not articles:
            return {"status": "success", "translated": 0, "chars": 0}
        texts = [text for _, title, summary in articles for text in (title, summary)]
        result = translate(texts, api_key=api_key, client=client)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        with Session(engine) as db, db.begin():
            for i, (key, _, _) in enumerate(articles):
                db.merge(NewsTranslation(url_hash=key, lang=LANG, title=result[2 * i],
                                         summary=result[2 * i + 1], provider=PROVIDER, translated_at=now))
    except TranslationError as exc:
        return {"status": "failed", "error_code": exc.code, "http_status": exc.status_code, "translated": 0}
    except SQLAlchemyError:
        return {"status": "failed", "error_code": "database_write", "translated": 0}
    return {"status": "success", "translated": len(articles), "chars": sum(map(len, texts))}


class TranslationSkipped(RuntimeError):
    """No API key configured; nothing was sent."""


def run_scheduled(*, engine_factory=get_engine, execute=run_translation) -> dict:
    """Airflow entry point: skipped without a key, raises on failure (quota/rate limits retry next run)."""
    result = execute(engine_factory(), api_key=get_settings().deepl_api_key.get_secret_value())
    if result["status"] == "skipped":
        raise TranslationSkipped(result["error_code"])
    if result["status"] != "success":
        raise RuntimeError(f"Translation failed: {result['error_code']}")
    return result


def main(argv=None, *, client=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=BATCH)
    parser.add_argument("--execute", action="store_true", help="Call DeepL and store translations")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= BATCH:
        print(json.dumps({"status": "failed", "error_code": "invalid_options"}))
        return 2
    try:
        engine = get_engine()
    except (RuntimeError, ValueError, OSError):
        print(json.dumps({"status": "failed", "error_code": "database_configuration"}))
        return 2
    if not args.execute:
        with Session(engine) as db:
            print(json.dumps({"status": "dry_run", "pending": len(pending(db, args.limit))}))
        return 0
    key = get_settings().deepl_api_key.get_secret_value()
    result = run_translation(engine, api_key=key, limit=args.limit, client=client)
    print(json.dumps(result))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())
