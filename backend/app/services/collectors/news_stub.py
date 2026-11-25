"""뉴스/산업동향 수집 어댑터 스텁.

실서비스 구현 시 후보:
- 네이버 검색 API (뉴스 검색, 일일 호출 제한, 상업적 이용 약관 확인 필요)
- RSS 수집 (언론사별 저작권·저장 허용 범위 확인 필요)
- 유료 뉴스 API (빅카인즈 등)

현재는 스텁 — 수집 없이 빈 결과를 반환한다.
"""
from datetime import datetime

from ...config import NEWS_API_KEY
from .base import CollectorResult


class NewsCollector:
    name = "news"

    @property
    def enabled(self) -> bool:
        return bool(NEWS_API_KEY)

    def collect(self, company_id: int | None = None) -> CollectorResult:
        res = CollectorResult(source="(미설정) 뉴스 수집", fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("NEWS_API_KEY 미설정 — 수집 비활성")
            return res
        # TODO(Phase B): 검색어(기업 업종·핵심 원자재) 기반 뉴스 수집 → NewsItem 매핑
        res.errors.append("미구현 — Phase B에서 실제 호출 구현 예정")
        return res
