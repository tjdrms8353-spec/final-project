"""Bounded RSS retries. Long server delays defer work rather than retry early."""
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from .rss import collect_rss, RssCollectionError


def retry_delay(value):
    if value is None:
        return None
    try:
        if value.strip().isdigit():
            return int(value.strip())
        return max(0, (parsedate_to_datetime(value).astimezone(timezone.utc) - datetime.now(timezone.utc)).total_seconds())
    except (ValueError, TypeError, OverflowError):
        return None


def collect_with_retry(*, attempts=3, sleep=time.sleep, on_attempt=None, **kwargs):
    if type(attempts) is not int or not 1 <= attempts <= 3:
        raise ValueError("attempts must be between 1 and 3")
    for number in range(1, attempts + 1):
        if on_attempt:
            on_attempt(number)
        try:
            return collect_rss(**kwargs)
        except RssCollectionError as exc:
            exc.attempts = number
            transient = exc.code in ("timeout", "network") or exc.status_code in (429, 500, 502, 503, 504)
            if not transient or number == attempts:
                raise
            delay = max(2 ** number, exc.retry_after or 0)
            if delay > 30:
                # Caller can schedule a later run; never shorten Retry-After.
                raise
            sleep(delay)
