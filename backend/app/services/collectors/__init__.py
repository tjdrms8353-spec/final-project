"""외부 데이터 수집 어댑터 패키지.

각 어댑터는 `Collector` 인터페이스를 구현한다.
현재는 인터페이스와 스텁만 정의되어 있으며, 실제 API 연동은
`docs/PRODUCTION_TRANSITION_PLAN.md` Phase B 에서 구현한다.
"""
from .base import Collector, CollectorResult  # noqa: F401
