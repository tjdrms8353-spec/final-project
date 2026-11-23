"""Registered public RSS feeds; one request, no article scraping or persistence."""

import hashlib
import math
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urldefrag
from xml.etree import ElementTree

import httpx
from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.features.trends.preprocessing.news import NewsBatch, prepare_news

FEED_URL = "https://feeds.bbci.co.uk/news/technology/rss.xml"
FEEDS = {
    "bbc-tech": (FEED_URL, "BBC News"),
    # Official directory: https://www.hankyung.com/feed
    "hankyung-it": ("https://www.hankyung.com/feed/it", "한국경제"),
    # Official directory/usage terms: https://news.sbs.co.kr/news/rss.do
    # Personal non-commercial use; commercial use requires publisher permission.
    "sbs-latest": ("https://news.sbs.co.kr/news/newsflashRssFeed.do?plink=RSSREADER", "SBS 뉴스"),
    # Korean feeds verified 2026-11-19. Title, link and date only; no article bodies.
    # Usage terms: https://www.yna.co.kr/rss/index (personal non-commercial use only)
    "yna-all": ("https://www.yna.co.kr/rss/news.xml", "연합뉴스"),
    # Usage terms: https://m.yonhapnewstv.co.kr/add/rss (no commercial distribution)
    "yonhapnewstv-latest": ("https://www.yonhapnewstv.co.kr/browse/feed/", "연합뉴스TV"),
    "donga-all": ("https://rss.donga.com/total.xml", "동아일보"),
    "hankyung-all": ("https://www.hankyung.com/feed/all-news", "한국경제"),
    "newsis-sokbo": ("https://www.newsis.com/RSS/sokbo.xml", "뉴시스"),
    "chosun-all": ("https://www.chosun.com/arc/outboundfeeds/rss/?outputType=xml", "조선일보"),
    "ohmynews-all": ("https://rss.ohmynews.com/rss/ohmynews.xml", "오마이뉴스"),
    "khan-all": ("https://www.khan.co.kr/rss/rssdata/total_news.xml", "경향신문"),
    "hani-all": ("https://www.hani.co.kr/rss", "한겨레"),
}
# Publisher section feeds verified 2026-11-19 (official lists: yna.co.kr/rss/index,
# rss.donga.com, hankyung.com/feed, news.sbs.co.kr/news/rss.do, m.yonhapnewstv.co.kr/add/rss).
# Feed -> verbatim section label. Normalizing labels across publishers is a later step.
_SBS = "https://news.sbs.co.kr/news/SectionRssFeed.do?sectionId={}&plink=RSSREADER"
_SECTIONS = {
    ("yna", "연합뉴스", "https://www.yna.co.kr/rss/{}.xml"): {
        "politics": "정치", "northkorea": "북한", "economy": "경제", "industry": "산업",
        "society": "사회", "international": "세계", "culture": "문화", "health": "건강",
        "entertainment": "연예", "sports": "스포츠"},
    ("donga", "동아일보", "https://rss.donga.com/{}.xml"): {
        "politics": "정치", "national": "사회", "economy": "경제", "international": "국제",
        "science": "의학과학", "culture": "문화연예", "sports": "스포츠", "health": "건강"},
    ("hankyung", "한국경제", "https://www.hankyung.com/feed/{}"): {
        "politics": "정치", "economy": "경제", "finance": "증권", "realestate": "부동산",
        "it": "IT", "international": "국제", "society": "사회", "life": "생활",
        "sports": "스포츠", "entertainment": "연예"},
    ("yonhapnewstv", "연합뉴스TV", "https://www.yonhapnewstv.co.kr/category/news/{}/feed/"): {
        "politics": "정치", "economy": "경제", "society": "사회", "international": "세계",
        "culture": "문화·연예", "sports": "스포츠"},
}
SECTION_FEEDS: dict[str, str] = {}
for (_prefix, _name, _url), _labels in _SECTIONS.items():
    for _slug, _label in _labels.items():
        FEEDS.setdefault(f"{_prefix}-{_slug}", (_url.format(_slug), _name))
        SECTION_FEEDS[f"{_prefix}-{_slug}"] = _label
for _slug, _code, _label in [
    ("politics", "01", "정치"), ("economy", "02", "경제"), ("society", "03", "사회"),
    ("international", "07", "국제"), ("culture", "08", "생활·문화"),
    ("entertainment", "14", "연예"), ("sports", "09", "스포츠"),
]:
    FEEDS[f"sbs-{_slug}"] = (_SBS.format(_code), "SBS 뉴스")
    SECTION_FEEDS[f"sbs-{_slug}"] = _label
# Feeds whose items carry clean <category> sections (SBS tags mix keywords, so excluded).
INLINE_SECTION_FEEDS = {"ohmynews-all", "khan-all"}
MAX_LABEL = 100
# Feeds whose short <description> is stored as summary (for translation). Korean feeds
# are excluded: some put article bodies there, and we keep title/link/date only.
SUMMARY_FEEDS = {"bbc-tech"}
MAX_SUMMARY = 1000
# Feeds without per-item dates. The collection time is stored as observed_at;
# storage keeps the first stored row, so it means "first observed".
OBSERVED_TIME_FEEDS = {"hani-all"}
DC_DATE = "{http://purl.org/dc/elements/1.1/}date"
# Identify the collector instead of the library default; hankyung.com rejects python-httpx with 403.
USER_AGENT = "FinalProjectNewsBot/0.1 (personal non-commercial RSS reader)"
MAX_BYTES = 2 * 1024 * 1024
_URL = TypeAdapter(HttpUrl)


class RssCollectionError(RuntimeError):
    def __init__(self, code: str, status_code: int | None = None):
        self.code = code
        self.status_code = status_code
        self.retry_after = None
        super().__init__(f"RSS collection failed: {code}")


def validate_options(limit: int, timeout: float = 20) -> None:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be finite and positive")


def parse_date(value: str | None) -> datetime | None:
    """RFC 822 (RSS 2 pubDate) or ISO 8601 (dc:date). Naive values fail validation later."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return parsedate_to_datetime(value)
    except (ValueError, TypeError, OverflowError):
        pass
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def parse_feed(payload: bytes, *, limit: int = 5, feed: str = "bbc-tech") -> NewsBatch:
    """Validate at most limit entries from a UTF-8 RSS 2 feed, then deduplicate."""
    validate_options(limit)
    if feed not in FEEDS:
        raise ValueError("Unknown feed")
    if len(payload) > MAX_BYTES:
        raise RssCollectionError("response_too_large")
    try:
        text = payload.decode("utf-8-sig")
        if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
            raise RssCollectionError("unsafe_xml")
        root = ElementTree.fromstring(text)
    except (UnicodeDecodeError, ElementTree.ParseError):
        raise RssCollectionError("invalid_xml") from None
    channel = root.find("channel")
    if root.tag != "rss" or channel is None:
        raise RssCollectionError("invalid_feed")
    records = []
    labels_by_id: dict[str, list[str]] = {}
    observed = datetime.now(timezone.utc) if feed in OBSERVED_TIME_FEEDS else None
    for entry in channel.findall("item")[:limit]:
        link = (entry.findtext("link") or "").strip()
        try:
            key = urldefrag(str(_URL.validate_python(link))).url
            identifier = "rss-" + hashlib.sha256(key.encode()).hexdigest()
        except ValidationError:
            identifier = ""
        date = entry.findtext("pubDate") or entry.findtext(DC_DATE)
        records.append({
            "id": identifier, "title": entry.findtext("title") or "",
            "url": link, "source": FEEDS[feed][1], "published_at": parse_date(date),
            "observed_at": observed,
            "summary": " ".join(re.sub(r"<[^>]*>", " ", entry.findtext("description") or "").split())[:MAX_SUMMARY]
            if feed in SUMMARY_FEEDS else "",
        })
        if feed in SECTION_FEEDS:
            labels = [SECTION_FEEDS[feed]]
        elif feed in INLINE_SECTION_FEEDS:
            labels = [" ".join(c.text.split())[:MAX_LABEL] for c in entry.findall("category") if c.text and c.text.strip()]
        else:
            labels = []
        if identifier and labels:
            labels_by_id[identifier] = list(dict.fromkeys(labels_by_id.get(identifier, []) + labels))
    batch = prepare_news(records)
    batch.sections = {item.id: labels_by_id[item.id] for item in batch.items if item.id in labels_by_id}
    return batch


def collect_rss(*, limit: int = 5, timeout: float = 20, client: httpx.Client | None = None, feed: str = "bbc-tech") -> NewsBatch:
    validate_options(limit, timeout)
    if feed not in FEEDS:
        raise ValueError("Unknown feed")

    def fetch(active: httpx.Client) -> NewsBatch:
        try:
            with active.stream("GET", FEEDS[feed][0], timeout=timeout, follow_redirects=False) as response:
                response.raise_for_status()
                payload = bytearray()
                for chunk in response.iter_bytes():
                    payload.extend(chunk)
                    if len(payload) > MAX_BYTES:
                        raise RssCollectionError("response_too_large")
        except httpx.TimeoutException:
            raise RssCollectionError("timeout") from None
        except httpx.HTTPStatusError as exc:
            from .retry import retry_delay
            error = RssCollectionError("http_status", exc.response.status_code)
            error.retry_after = retry_delay(exc.response.headers.get("retry-after"))
            raise error from None
        except httpx.RequestError:
            raise RssCollectionError("network") from None
        return parse_feed(bytes(payload), limit=limit, feed=feed)

    if client is not None:
        return fetch(client)
    with httpx.Client(headers={"User-Agent": USER_AGENT}) as active:
        return fetch(active)
