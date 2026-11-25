"""위험 영향 시뮬레이션"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import SimulationParams
from ..services.simulation import run_simulation

router = APIRouter(prefix="/api/simulation", tags=["simulation"])

SEVERITY_DESC = {
    "정상": "영향이 연간 영업이익의 3% 미만 — 지속 모니터링 수준",
    "관심": "영향이 3~7% — 분기 내 대응 계획 수립 권장",
    "주의": "영향이 7~15% — 원가·결제 정책 조정 검토 필요",
    "위험": "영향이 15~30% — 경영진 보고 및 대응 시나리오 수립 필요",
    "심각": "영향이 30% 이상 — 즉시 대응 계획 수립 필요",
}


@router.get("/presets")
def presets(user: User = Depends(get_current_user)):
    return {
        "defaults": SimulationParams().model_dump(),
        "presets": [
            {"name": "환율 급등 시나리오", "params": {"fx_change_pct": 5.0}},
            {"name": "금리 인상 시나리오", "params": {"rate_change_pct": 1.0}},
            {"name": "원자재 가격 상승 시나리오", "params": {"material_change_pct": 10.0}},
            {"name": "수요 둔화 시나리오", "params": {"revenue_change_pct": -8.0}},
            {"name": "복합 위기 시나리오", "params": {"fx_change_pct": 4.0, "rate_change_pct": 0.75,
                                                    "material_change_pct": 8.0, "revenue_change_pct": -5.0}},
        ],
        "severity_rules": SEVERITY_DESC,
    }


@router.post("/run")
def simulate(body: SimulationParams, user: User = Depends(get_current_user),
             db: Session = Depends(get_db)):
    return run_simulation(db, user.company_id, body)
