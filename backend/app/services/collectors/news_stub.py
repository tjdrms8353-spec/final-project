"""뉴스 수집 어댑터 — RSS 피드 기반 (API 키 불필요).

- NEWS_RSS_URLS 환경변수의 피드 목록(쉼표 구분)을 수집한다.
- 기본값: Google 뉴스 RSS 검색(환율/수출입/원자재).
- NEWS_COLLECT_ENABLED=0이면 비활성.
- 파싱은 표준 라이브러리 xml.etree만 사용(추가 의존성 없음).
- 저작권: 제목·요약·링크만 저장하고 원문 전재는 하지 않는다.
"""
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime

from ...config import NEWS_COLLECT_ENABLED, NEWS_RSS_URLS
from .base import CollectorResult, get_text

MAX_ITEMS_PER_FEED = 30

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _parse_date(raw: str) -> datetime:
    try:
        d = parsedate_to_datetime(raw)
        return d.replace(tzinfo=None)
    except (TypeError, ValueError):
        return datetime.utcnow()


def parse_rss(xml_text: str, feed_source: str) -> list[dict]:
    """RSS 2.0 XML을 NewsItem 매핑 dict 목록으로 변환한다."""
    root = ET.fromstring(xml_text)
    items: list[dict] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        if not title:
            continue
        src_el = item.find("source")
        source = (src_el.text or "").strip() if src_el is not None and src_el.text else feed_source
        items.append({
            "title": title[:490],
            "summary": _strip_html(item.findtext("description"))[:2000],
            "source": source or feed_source,
            "link": (item.findtext("link") or "").strip()[:490],
            "published_at": _parse_date(item.findtext("pubDate") or ""),
        })
        if len(items) >= MAX_ITEMS_PER_FEED:
            break
    return items


class NewsCollector:
    name = "news_rss"
    source = "RSS 뉴스 수집"
    # Google 뉴스 RSS는 상업적 이용 조건이 불명확 — 운영 기본 비활성
    # (docs/DATA_LICENSES.md, ALLOW_UNVERIFIED_SOURCES=1로 강제 가능)
    license_verified = False

    @property
    def enabled(self) -> bool:
        return NEWS_COLLECT_ENABLED and bool(NEWS_RSS_URLS.strip())

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("NEWS_COLLECT_ENABLED=0 또는 RSS URL 미설정 — 수집 비활성")
            return res
        urls = [u.strip() for u in NEWS_RSS_URLS.split(",") if u.strip()]
        for url in urls:
            feed = url.split("/")[2] if "://" in url else url
            try:
                xml_text = get_text(url)
                res.news.extend(parse_rss(xml_text, feed))
            except Exception as e:
                res.errors.append(f"RSS 수집 실패 ({feed}): {e}")
        return res
