from collections.abc import Iterable
from dataclasses import dataclass, field
from urllib.parse import urldefrag

from pydantic import ValidationError

from app.features.trends.schemas import NewsItem


@dataclass
class RejectedNews:
    index: int
    # Retain field names/error codes only, never the original article payload.
    errors: list[dict[str, object]]


@dataclass
class NewsBatch:
    items: list[NewsItem] = field(default_factory=list)
    rejected: list[RejectedNews] = field(default_factory=list)
    input_count: int = 0
    duplicate_count: int = 0
    # Accepted item id -> publisher section labels (empty when the feed has none).
    sections: dict[str, list[str]] = field(default_factory=dict)


def prepare_news(records: Iterable[object]) -> NewsBatch:
    """Keep the first valid ID/URL, then sort by publication time descending.

    URL fragments are ignored for duplicate detection. Query parameters, paths
    and HTTP/HTTPS remain distinct to avoid merging different articles.
    Rejected indices refer to the zero-based input order.
    """
    batch = NewsBatch()
    seen_ids: set[str] = set()
    seen_urls: set[str] = set()
    for index, record in enumerate(records):
        batch.input_count += 1
        try:
            item = NewsItem.model_validate(record)
        except ValidationError as exc:
            batch.rejected.append(RejectedNews(
                index=index,
                errors=[
                    {"field": ".".join(str(part) for part in error["loc"]),
                     "code": error["type"]}
                    for error in exc.errors(include_url=False, include_input=False)
                ],
            ))
            continue

        url_key = urldefrag(str(item.url)).url
        if item.id in seen_ids or url_key in seen_urls:
            batch.duplicate_count += 1
            continue
        seen_ids.add(item.id)
        seen_urls.add(url_key)
        batch.items.append(item)

    batch.items.sort(
        key=lambda item: item.published_at or item.observed_at, reverse=True,
    )
    return batch
