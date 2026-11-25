"""외부 데이터 수집 어댑터 공통 인터페이스.

설계 의도:
- 수집 원천(EXIM 환율, ECOS, DART, 뉴스 등)이 달라도 동일한 반환 스키마를 강제한다.
- 결과는 `MarketSeries`/`NewsItem`에 바로 매핑 가능한 dict 목록이다.
- 수집 실패는 예외로 던지지 않고 `errors`에 기록해 호출자가 판단한다.
- API 키는 config의 환경변수에서 읽으며, 미설정 시 `enabled == False`.
"""
from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class CollectorResult:
    source: str                    # 수집 원천 표기 (예: "한국수출입은행")
    series: list[dict] = field(default_factory=list)   # MarketSeries용 {series_key, series_name, unit, month, value}
    news: list[dict] = field(default_factory=list)      # NewsItem용 {title, summary, source, category, published_at, ...}
    fetched_at: str = ""
    errors: list[str] = field(default_factory=list)


class Collector(Protocol):
    """수집 어댑터가 구현해야 하는 인터페이스."""
    name: str

    @property
    def enabled(self) -> bool:
        """필수 API 키가 설정되어 실제 수집 가능한지 여부."""
        ...

    def collect(self, company_id: int | None = None) -> CollectorResult:
        """데이터를 수집해 표준 결과로 반환한다."""
        ...
