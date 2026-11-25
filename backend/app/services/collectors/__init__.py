"""외부 데이터 수집 어댑터 패키지 (정식 전환 B).

- EximFxCollector : 한국수출입은행 환율 (EXIM_API_KEY 필요)
- EcosRateCollector : 한국은행 기준금리 (ECOS_API_KEY 필요)
- NewsCollector : RSS 뉴스 수집 (키 불필요, NEWS_RSS_URLS 사용)

모든 어댑터는 `Collector` 인터페이스를 구현하고 `CollectorResult`를 반환한다.
저장·중복 차단·기업별 복제는 `services.collection_service`가 담당한다.
"""
from .base import Collector, CollectorError, CollectorResult  # noqa: F401
from .fx_ecos import EcosRateCollector, EximFxCollector  # noqa: F401
from .news_stub import NewsCollector  # noqa: F401

ALL_COLLECTORS = [EximFxCollector, EcosRateCollector, NewsCollector]
