"""LLM 분석 모듈 인터페이스 — 규칙 기반 엔진의 교체 지점.

설계 의도:
- `run_analysis(db, company_id, trigger)` 하나로 호출부(analysis router, 파이프라인)와 분리한다.
- LLM 설정(LLM_API_KEY/LLM_BASE_URL/LLM_MODEL)이 없으면 규칙 기반 엔진으로 폴백한다.
- LLM 구현 시 반환 스키마는 AnalysisResult 필드와 동일해야 하며,
  근거·불확실성·데이터 출처·"사람이 최종 의사결정" 면책을 반드시 포함한다.
- Phase C에서 OpenAI 호환 API(/v1/chat/completions) 호출을 구현한다.
"""
from sqlalchemy.orm import Session

from ..config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL
from .analysis_engine import run_analyses as rule_run_analyses


def llm_enabled() -> bool:
    """LLM 분석 사용 가능 여부 (키·엔드포인트·모델 모두 설정된 경우)."""
    return bool(LLM_API_KEY and LLM_BASE_URL and LLM_MODEL)


def run_llm_analyses(db: Session, company_id: int, trigger: str = "manual"):
    """LLM 기반 분석. 미구현/미설정 시 None을 반환해 호출자가 폴백한다."""
    if not llm_enabled():
        return None
    # TODO(Phase C): KPI 컨텍스트 구성 → LLM 호출 → JSON 스키마 검증 → AnalysisResult 생성
    # 실패·스키마 불일치 시 None 반환하여 규칙 엔진 폴백 유지
    return None


def run_analysis(db: Session, company_id: int, trigger: str = "manual"):
    """분석 실행 진입점. LLM 우선, 실패 시 규칙 기반 엔진 폴백."""
    results = run_llm_analyses(db, company_id, trigger)
    if results:
        return results
    return rule_run_analyses(db, company_id, trigger)
