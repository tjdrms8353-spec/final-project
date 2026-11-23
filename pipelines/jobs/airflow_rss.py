"""Airflow task logic without importing Airflow, so it is testable on any OS.

Reuses execute_stored: same lock, run history and bounded in-process retries.
"""
from app.db.session import get_engine
from app.features.trends.collectors.rss import FEEDS, SECTION_FEEDS, validate_options
from pipelines.jobs.rss_history import execute_stored

# Feed -> interval minutes. Minimum 5 minutes, matching the local scheduler.
# Korean news every 5 minutes; BBC follows its <ttl>15</ttl>.
KOREAN_FEEDS = (
    "sbs-latest", "yna-all", "yonhapnewstv-latest", "donga-all", "hankyung-all",
    "newsis-sokbo", "chosun-all", "ohmynews-all", "khan-all", "hani-all",
)
# Section feeds exist for labels; their shortest retention was 1.3 h (2026-11-19), so 30 min suffices.
# hankyung-it is a section feed too and is scheduled here.
SECTION_INTERVAL = 30
SCHEDULES = {"bbc-tech": 15, **dict.fromkeys(KOREAN_FEEDS, 5),
             **dict.fromkeys(SECTION_FEEDS, SECTION_INTERVAL)}
# Read the whole feed each run so articles published between runs are not missed.
# Checked 2026-11-19: BBC 21 items, SBS 101 items (~0.8 MB) per response.
FEED_LIMIT = 100


class CollectionSkipped(RuntimeError):
    """Another run of the same feed holds the lock; no external request was sent."""


class CollectionFailed(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__(f"RSS collection failed: {result.get('error_code') or result.get('status')}")


def validate_schedules(schedules):
    if not schedules or any(feed not in FEEDS or type(minutes) is not int or minutes < 5
                            for feed, minutes in schedules.items()):
        raise ValueError("Each registered feed requires an integer interval of at least 5 minutes")


def run_feed(feed, *, limit=FEED_LIMIT, timeout=20, engine_factory=get_engine, execute=execute_stored):
    validate_options(limit, timeout)
    if feed not in FEEDS:
        raise ValueError("Unknown feed")
    result = execute(engine_factory(), feed=feed, limit=limit, timeout=timeout)
    if result.get("error_code") == "collection_busy":
        raise CollectionSkipped(feed)
    # partial means the batch had invalid items and nothing was stored.
    if result["status"] != "success":
        raise CollectionFailed(result)
    return result
