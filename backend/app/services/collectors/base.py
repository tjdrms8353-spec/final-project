"""외부 데이터 수집 어댑터 공통 인터페이스.

설계 의도:
- 수집 원천(EXIM 환율, ECOS, 뉴스 RSS 등)이 달라도 동일한 반환 스키마를 강제한다.
- 결과는 `MarketSeries`/`NewsItem`에 바로 매핑 가능한 dict 목록이다.
- 수집 실패는 예외로 던지지 않고 `errors`에 기록해 호출자가 판단한다.
- API 키는 config의 환경변수에서 읽으며, 미설정 시 `enabled == False`.
- HTTP 호출은 get_json/get_text로 통일 — 테스트에서 이 함수들을 교체해 검증한다.
"""
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from ...config import COLLECT_TIMEOUT_SEC


class CollectorError(Exception):
    """수집 HTTP 요청 실패."""


def get_json(url: str, params: dict | None = None):
    """JSON 응답을 반환한다. 실패 시 CollectorError."""
    try:
        r = httpx.get(url, params=params, timeout=COLLECT_TIMEOUT_SEC,
                      follow_redirects=True)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        raise CollectorError(f"GET {url} 실패: {e}") from e


def get_text(url: str, params: dict | None = None) -> str:
    """텍스트(RSS/XML 등) 응답을 반환한다. 실패 시 CollectorError."""
    try:
        r = httpx.get(url, params=params, timeout=COLLECT_TIMEOUT_SEC,
                      follow_redirects=True,
                      headers={"User-Agent": "dayribbon-collector/0.1"})
        r.raise_for_status()
        return r.text
    except Exception as e:
        raise CollectorError(f"GET {url} 실패: {e}") from e


@dataclass
class CollectorResult:
    source: str                    # 수집 원천 표기 (예: "한국수출입은행")
    series: list[dict] = field(default_factory=list)   # MarketSeries용 {series_key, series_name, unit, month, value}
    news: list[dict] = field(default_factory=list)      # NewsItem용 {title, summary, source, category, published_at, link, ...}
    fetched_at: str = ""
    errors: list[str] = field(default_factory=list)


class Collector(Protocol):
    """수집 어댑터가 구현해야 하는 인터페이스."""
    name: str
    source: str                    # 출처 표기명

    @property
    def enabled(self) -> bool:
        """필수 API 키가 설정되어 실제 수집 가능한지 여부."""
        ...

    def collect(self) -> CollectorResult:
        """데이터를 수집해 표준 결과로 반환한다."""
        ...
