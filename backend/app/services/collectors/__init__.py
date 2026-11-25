"""외부 데이터 수집 어댑터 패키지 (정식 전환 B 보완).

- EximFxCollector : 한국수출입은행 환율 (EXIM_API_KEY 필요)
- EcosRateCollector : 한국은행 기준금리 (ECOS_API_KEY 필요)
- NewsCollector : RSS 뉴스 수집 (키 불필요, 이용 조건 미검증 → 운영 기본 비활성)
- GdeltNewsCollector : GDELT 뉴스 (오픈 데이터, 키 불필요)
- FredSeriesCollector : FRED 환율·금리·유가 (FRED_API_KEY 필요)
- EiaSeriesCollector : EIA 유가 (EIA_API_KEY 필요)
- DartDisclosureCollector : OpenDART 공시 (DART_API_KEY + DART_CORP_CODES 필요)

collector_active()는 키/설정 + 이용 조건 검증 여부를 함께 판단한다.
저장·중복 차단·기업별 연결은 services.collection_service가 담당한다.
"""
from ...config import ALLOW_UNVERIFIED_SOURCES, IS_PROD
from .base import Collector, CollectorError, CollectorResult  # noqa: F401
from .fx_ecos import EcosRateCollector, EximFxCollector  # noqa: F401
from .global_sources import (  # noqa: F401
    DartDisclosureCollector, EiaSeriesCollector, FredSeriesCollector,
    GdeltNewsCollector,
)
from .news_stub import NewsCollector  # noqa: F401

ALL_COLLECTORS = [
    EximFxCollector, EcosRateCollector, NewsCollector,
    GdeltNewsCollector, FredSeriesCollector, EiaSeriesCollector,
    DartDisclosureCollector,
]


def collector_active(collector) -> bool:
    """수집기가 실제 실행 가능한지 — 키/설정 + 이용 조건 검증을 함께 판단.

    이용 조건이 미검증인 공급처(license_verified=False)는 운영 환경에서
    ALLOW_UNVERIFIED_SOURCES=1이 없으면 실행하지 않는다.
    """
    if not collector.enabled:
        return False
    if IS_PROD and not getattr(collector, "license_verified", True) \
            and not ALLOW_UNVERIFIED_SOURCES:
        return False
    return True
