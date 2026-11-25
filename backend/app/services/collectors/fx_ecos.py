"""환율/금리 수집 어댑터 스텁 — 한국수출입은행 EXIM + 한국은행 ECOS.

실서비스 구현 시:
- EXIM: https://www.koreaexim.go.kr (환율, 무료·비영리 목적 확인 필요)
- ECOS: https://ecos.bok.or.kr (기준금리·통계, 오픈API 키 발급)
- 상업적 이용·저장·가공 허용 범위를 각 API 약관에서 확인 후 활성화할 것.

현재는 스텁 — `enabled`가 False이며 collect()는 빈 결과를 반환한다.
"""
from datetime import datetime

from ...config import ECOS_API_KEY, EXIM_API_KEY
from .base import CollectorResult


class EximFxCollector:
    name = "exim_fx"

    @property
    def enabled(self) -> bool:
        return bool(EXIM_API_KEY)

    def collect(self, company_id: int | None = None) -> CollectorResult:
        res = CollectorResult(source="한국수출입은행 EXIM", fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("EXIM_API_KEY 미설정 — 수집 비활성")
            return res
        # TODO(Phase B): GET https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON
        #  → USD_KRW series_key로 MarketSeries 매핑
        res.errors.append("미구현 — Phase B에서 실제 호출 구현 예정")
        return res


class EcosRateCollector:
    name = "ecos_rate"

    @property
    def enabled(self) -> bool:
        return bool(ECOS_API_KEY)

    def collect(self, company_id: int | None = None) -> CollectorResult:
        res = CollectorResult(source="한국은행 ECOS", fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("ECOS_API_KEY 미설정 — 수집 비활성")
            return res
        # TODO(Phase B): ECOS StatisticSearch → BASE_RATE 등 시계열 매핑
        res.errors.append("미구현 — Phase B에서 실제 호출 구현 예정")
        return res
