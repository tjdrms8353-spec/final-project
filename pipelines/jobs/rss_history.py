"""Persist history for explicit --execute --store jobs; no implicit retries."""
from datetime import datetime, timezone
from uuid import uuid4
import hashlib
import socket
from pathlib import Path
from sqlalchemy import update

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.features.trends.collectors.rss import collect_rss, RssCollectionError
from app.features.trends.models import CollectionRun
from app.features.trends.repository import store_news, store_sections, utc_naive
from pipelines.jobs.collection_lock import collection_lock, CollectionBusy
from app.features.trends.collectors.retry import collect_with_retry


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def owner_id():
    # Same scope as the local project lock. Other machines/checkouts are untouched.
    identity = socket.gethostname() + ':' + str(Path(__file__).resolve().parents[2])
    return hashlib.sha256(identity.encode()).hexdigest()


def recover_locked(db, feed, owner):
    """Caller must hold the feed's exclusive OS lock; timestamp is detection time."""
    result = db.execute(update(CollectionRun).where(
        CollectionRun.feed == feed, CollectionRun.owner_id == owner,
        CollectionRun.status == 'running',
    ).values(status='interrupted', finished_at=now(), error_code='previous_process_interrupted'))
    return result.rowcount


def execute_stored(engine, *, feed, limit, timeout, client=None):
    try:
        with collection_lock(feed):
            return _execute_stored(engine, feed=feed, limit=limit, timeout=timeout, client=client)
    except CollectionBusy:
        return {"status": "failed", "error_code": "collection_busy", "storage": "not_started"}


def _execute_stored(engine, *, feed, limit, timeout, client=None):
    run_id = str(uuid4())
    owner = owner_id()
    try:
        with Session(engine) as db, db.begin():
            recover_locked(db, feed, owner)
            db.add(CollectionRun(run_id=run_id, feed=feed, owner_id=owner, started_at=now(), status="running"))
    except SQLAlchemyError:
        return {"status": "failed", "error_code": "database_write", "history": "unavailable"}
    counts = {}
    try:
        batch = collect_with_retry(feed=feed, limit=limit, timeout=timeout, client=client,
                                   on_attempt=lambda number: counts.update(attempt_count=number))
        attempt_count = counts["attempt_count"]
        counts = dict(input_count=batch.input_count, accepted_count=len(batch.items),
                      rejected_count=len(batch.rejected), duplicate_count=batch.duplicate_count)
        counts["attempt_count"] = attempt_count
        status = "partial" if batch.rejected else "success"
        if batch.rejected and not batch.items:
            status = "failed"
        with Session(engine) as db, db.begin():
            run = db.get(CollectionRun, run_id)
            for key, value in counts.items():
                setattr(run, key, value)
            run.inserted_count = run.existing_count = 0
            dated = [item.published_at for item in batch.items if item.published_at]
            run.window_start_at = utc_naive(min(dated)) if dated else None
            if not batch.rejected:
                stored = store_news(db, batch.items)
                run.inserted_count, run.existing_count = stored.inserted, stored.existing
                store_sections(db, batch.items, batch.sections, feed, seen_at=datetime.now(timezone.utc))
            run.status, run.finished_at = status, now()
            run.error_code = "invalid_articles" if batch.rejected else None
            result = dict(run_id=run_id, status=status, **counts,
                          inserted_count=run.inserted_count, existing_count=run.existing_count,
                          storage="skipped_invalid_batch" if batch.rejected else "committed")
        return result
    except RssCollectionError as exc:
        code, http_status = exc.code, exc.status_code
    except SQLAlchemyError as exc:
        # Numeric driver error only (e.g. MySQL 1213 deadlock); never the message or SQL.
        number = getattr(getattr(exc, "orig", None), "args", (None,))[:1]
        number = number[0] if number and type(number[0]) is int else None
        code, http_status = f"database_write_{number}" if number else "database_write", None
    except Exception:
        code, http_status = "unexpected_error", None
    result = dict(run_id=run_id, status="failed", error_code=code, http_status=http_status, storage="rolled_back")
    try:
        with Session(engine) as db, db.begin():
            run = db.get(CollectionRun, run_id)
            run.status, run.finished_at = "failed", now()
            run.error_code, run.http_status = code, http_status
            run.inserted_count = run.existing_count = 0
            for key, value in counts.items():
                setattr(run, key, value)
    except SQLAlchemyError:
        result["history"] = "finalization_failed"
    return result
