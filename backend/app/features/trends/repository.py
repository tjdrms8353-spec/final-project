"""No connections or commits at import time; callers own the transaction."""

import hashlib
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from urllib.parse import urldefrag

from sqlalchemy import func, select
from sqlalchemy import insert, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import CollectionRun, NewsArticle, NewsArticleSection, NewsTranslation
from .schemas import CoverageGap, NewsItem, StoredNewsItem, NewsListResponse


@dataclass
class StoreResult:
    inserted: int = 0
    existing: int = 0


def utc_naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None) if value else None


def url_hash(item: NewsItem) -> str:
    return hashlib.sha256(urldefrag(str(item.url)).url.encode("utf-8")).hexdigest()


def _begin(session: Session) -> str:
    dialect = session.get_bind().dialect.name
    if dialect not in ("mysql", "sqlite"):
        raise ValueError("Supported database dialects: mysql (TiDB), sqlite (tests)")
    if dialect == "sqlite":
        connection = session.connection()
        if not connection.connection.driver_connection.in_transaction:
            connection.exec_driver_sql("BEGIN")
    return dialect


def _insert_new(session: Session, dialect: str, table, values: dict) -> bool:
    """Insert one row; False when the primary key already exists."""
    try:
        with session.begin_nested():
            session.execute(insert(table).values(**values))
        return True
    except IntegrityError as exc:
        code = getattr(exc.orig, "args", (None,))[0]
        sqlite_code = getattr(exc.orig, "sqlite_errorcode", None)
        if (dialect == "mysql" and code == 1062) or (dialect == "sqlite" and sqlite_code in (1555, 2067)):
            return False
        raise


def store_news(session: Session, items: Iterable[NewsItem]) -> StoreResult:
    """First stored version wins; URL fragments are ignored for deduplication.

    Exception: an empty stored summary is filled once when a later fetch provides one.
    Database primary key prevents duplicates even for simultaneous workers.
    Article revision updates and cross-URL issue grouping are separate work.
    """
    dialect = _begin(session)
    result = StoreResult()
    for item in items:
        key = url_hash(item)
        values = {
            "url_hash": key, "source_id": item.id, "url": urldefrag(str(item.url)).url,
            "title": item.title, "source": item.source, "summary": item.summary,
            "published_at": utc_naive(item.published_at),
            "observed_at": utc_naive(item.observed_at),
            "sort_at": utc_naive(item.published_at or item.observed_at),
        }
        if _insert_new(session, dialect, NewsArticle, values):
            result.inserted += 1
            continue
        result.existing += 1
        if item.summary:
            session.execute(update(NewsArticle).where(
                NewsArticle.url_hash == key, NewsArticle.summary == "").values(summary=item.summary))
    return result


def store_sections(session: Session, items: Iterable[NewsItem], sections: dict[str, list[str]],
                   feed: str, *, seen_at: datetime) -> int:
    """Add new (article, label) pairs; existing pairs keep their first feed and time."""
    dialect = _begin(session)
    added = 0
    for item in items:
        for label in sections.get(item.id, []):
            added += _insert_new(session, dialect, NewsArticleSection, {
                "url_hash": url_hash(item), "label": label, "feed": feed,
                "first_seen_at": utc_naive(seen_at),
            })
    return added


def collection_gaps(session: Session, *, since: datetime, now: datetime,
                    feed: str | None = None, unverified_after: timedelta = timedelta(hours=1)) -> list[CoverageGap]:
    """Periods per feed in which articles may be missing. All datetimes are UTC.

    missed: the feed's oldest item was newer than the previous successful fetch.
    unverified: no window recorded (old runs, undated feeds) and the interval is long.
    ongoing: the latest successful fetch is older than unverified_after.
    """
    query = select(CollectionRun.feed, CollectionRun.started_at, CollectionRun.window_start_at).where(
        CollectionRun.status == "success", CollectionRun.started_at >= utc_naive(since),
    ).order_by(CollectionRun.feed, CollectionRun.started_at)
    if feed:
        query = query.where(CollectionRun.feed == feed)
    runs: dict[str, list] = {}
    for row in session.execute(query):
        runs.setdefault(row.feed, []).append(row)
    aware = lambda value: value.replace(tzinfo=timezone.utc)
    gaps = []
    for name, rows in runs.items():
        for prev, cur in zip(rows, rows[1:]):
            if cur.window_start_at is not None:
                if cur.window_start_at > prev.started_at:
                    gaps.append(CoverageGap(feed=name, start=aware(prev.started_at),
                                            end=aware(cur.window_start_at), kind="missed"))
            elif cur.started_at - prev.started_at > unverified_after:
                gaps.append(CoverageGap(feed=name, start=aware(prev.started_at),
                                        end=aware(cur.started_at), kind="unverified"))
        last = aware(rows[-1].started_at)
        if now - last > unverified_after:
            gaps.append(CoverageGap(feed=name, start=last, end=None, kind="ongoing"))
    return gaps


def list_news(session: Session, *, limit: int = 20, offset: int = 0) -> list[NewsItem]:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if type(offset) is not int or offset < 0:
        raise ValueError("offset must be a non-negative integer")
    rows = session.scalars(select(NewsArticle).order_by(
        NewsArticle.sort_at.desc(), NewsArticle.url_hash.asc(),
    ).limit(limit).offset(offset))
    return [NewsItem(
        id=row.source_id, title=row.title, url=row.url, source=row.source,
        summary=row.summary,
        published_at=row.published_at.replace(tzinfo=timezone.utc) if row.published_at else None,
        observed_at=row.observed_at.replace(tzinfo=timezone.utc) if row.observed_at else None,
    ) for row in rows]


def _stored_item(row: NewsArticle, ko: NewsTranslation | None = None) -> StoredNewsItem:
    return StoredNewsItem(
        article_id=row.url_hash, id=row.source_id, title=row.title,
        url=row.url, source=row.source, summary=row.summary,
        published_at=row.published_at.replace(tzinfo=timezone.utc) if row.published_at else None,
        observed_at=row.observed_at.replace(tzinfo=timezone.utc) if row.observed_at else None,
        title_ko=ko.title if ko else None, summary_ko=(ko.summary or None) if ko else None,
    )


def _with_korean():
    return select(NewsArticle, NewsTranslation).outerjoin(NewsTranslation, (
        NewsTranslation.url_hash == NewsArticle.url_hash) & (NewsTranslation.lang == "ko"))


def search_news(session: Session, *, limit: int = 20, offset: int = 0,
                q: str | None = None, source: str | None = None) -> NewsListResponse:
    filters = []
    if q and q.strip():
        # User '%' and '_' are literal characters, not SQL wildcards.
        filters.append(NewsArticle.title.contains(q.strip(), autoescape=True))
    if source and source.strip():
        filters.append(NewsArticle.source == source.strip())
    total = session.scalar(select(func.count()).select_from(NewsArticle).where(*filters))
    rows = session.execute(_with_korean().where(*filters).order_by(
        NewsArticle.sort_at.desc(), NewsArticle.url_hash.asc(),
    ).limit(limit).offset(offset))
    return NewsListResponse(items=[_stored_item(row, ko) for row, ko in rows], total=total,
                            limit=limit, offset=offset)


def find_news(session: Session, article_id: str) -> StoredNewsItem | None:
    found = session.execute(_with_korean().where(NewsArticle.url_hash == article_id)).first()
    return _stored_item(*found) if found else None
