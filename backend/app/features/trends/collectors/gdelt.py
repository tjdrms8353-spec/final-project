"""One explicit GDELT DOC 2.0 request; no scheduler, retries or persistence.

Protocol reference: https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/
GDELT seendate is retained as observed_at, not an inferred publication time.
"""

import hashlib
import math
import re
from datetime import datetime, timezone
from urllib.parse import urldefrag

import httpx
from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.features.trends.preprocessing.news import NewsBatch, prepare_news

ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
_URL = TypeAdapter(HttpUrl)


class GdeltCollectionError(RuntimeError):
    def __init__(self, code: str, *, status_code: int | None = None):
        self.code = code
        self.status_code = status_code
        super().__init__(f"GDELT collection failed: {code}")


def _map_article(record: object) -> object:
    if not isinstance(record, dict):
        return record
    raw_url = record.get("url")
    try:
        url = _URL.validate_python(raw_url)
        key = urldefrag(str(url)).url
        article_id = "gdelt-" + hashlib.sha256(key.encode("utf-8")).hexdigest()
    except ValidationError:
        article_id = ""

    observed_at = None
    seen = record.get("seendate")
    if isinstance(seen, str) and re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", seen):
        try:
            observed_at = datetime.strptime(seen, "%Y%m%dT%H%M%SZ").replace(
                tzinfo=timezone.utc,
            )
        except ValueError:
            pass
    return {
        "id": article_id,
        "title": record.get("title"),
        "url": raw_url,
        "source": record.get("domain"),
        "observed_at": observed_at,
    }


def parse_gdelt_response(payload: object) -> NewsBatch:
    """Reject malformed envelopes; isolate invalid articles within a valid list."""
    if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
        raise GdeltCollectionError("invalid_payload")
    return prepare_news(_map_article(record) for record in payload["articles"])


def validate_collection_options(
    query: str,
    *,
    timespan: str = "1h",
    max_records: int = 50,
    timeout: float = 15.0,
) -> dict[str, str | int]:
    """Validate a request without creating a client or accessing the network."""
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query must be a non-empty string")
    if type(max_records) is not int or not 1 <= max_records <= 250:
        raise ValueError("max_records must be between 1 and 250")
    if not isinstance(timespan, str):
        raise ValueError("timespan must use minutes, hours or days")
    match = re.fullmatch(r"([1-9][0-9]*)(min|h|d)", timespan)
    if not match:
        raise ValueError("timespan must use minutes, hours or days")
    minutes = int(match[1]) * {"min": 1, "h": 60, "d": 1440}[match[2]]
    if not 15 <= minutes <= 7 * 1440:
        raise ValueError("This collector supports windows from 15 minutes to 7 days")
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout) or timeout <= 0):
        raise ValueError("timeout must be finite and positive")

    return {
        "query": query.strip(), "mode": "ArtList", "format": "json",
        "timespan": timespan, "maxrecords": max_records, "sort": "DateDesc",
    }


def collect_news(
    query: str,
    *,
    timespan: str = "1h",
    max_records: int = 50,
    timeout: float = 15.0,
    client: httpx.Client | None = None,
) -> NewsBatch:
    """Fetch one bounded result set, with no exhaustive pagination or retries.

    Injected clients remain owned by the caller. Failures do not echo request
    query strings or response bodies.
    """
    params = validate_collection_options(
        query, timespan=timespan, max_records=max_records, timeout=timeout,
    )

    def fetch(active_client: httpx.Client) -> NewsBatch:
        try:
            response = active_client.get(
                ENDPOINT, params=params, timeout=timeout, follow_redirects=False,
            )
            response.raise_for_status()
        except httpx.TimeoutException:
            raise GdeltCollectionError("timeout") from None
        except httpx.HTTPStatusError as exc:
            raise GdeltCollectionError(
                "http_status", status_code=exc.response.status_code,
            ) from None
        except httpx.RequestError:
            raise GdeltCollectionError("network") from None
        try:
            payload = response.json()
        except (ValueError, UnicodeDecodeError):
            raise GdeltCollectionError("invalid_json") from None
        return parse_gdelt_response(payload)

    if client is not None:
        return fetch(client)
    with httpx.Client() as active_client:
        return fetch(active_client)
