"""위험 영향 시뮬레이션 — 순수 계산 엔진 (외부 API 불필요)."""
from ..models import Company, FinancialMonthly
from ..utils import fmt_krw
from ..schemas import SimulationParams
from sqlalchemy.orm import Session


def _severity(total_impact: float, annual_op: float) -> tuple[str, str]:
    if not annual_op:
        return "정상", "영업이익 데이터가 없어 등급 산정 불가"
    ratio = abs(total_impact) / abs(annual_op) * 100
    if ratio < 3:
        return "정상", f"영업이익 대비 영향 {ratio:.1f}%"
    if ratio < 7:
        return "관심", f"영업이익 대비 영향 {ratio:.1f}%"
    if ratio < 15:
        return "주의", f"영업이익 대비 영향 {ratio:.1f}%"
    if ratio < 30:
        return "위험", f"영업이익 대비 영향 {ratio:.1f}%"
    return "심각", f"영업이익 대비 영향 {ratio:.1f}%"


def run_simulation(db: Session, company_id: int, p: SimulationParams) -> dict:
    company = db.get(Company, company_id)
    if not company:
        return {"error": "기업 정보를 찾을 수 없습니다."}

    # 최근 12개월 평균 원자재비율 → 한계공헌이익 근사치용 변동비율
    fin = (
        db.query(FinancialMonthly)
        .filter(FinancialMonthly.company_id == company_id)
        .order_by(FinancialMonthly.month.desc())
        .limit(12)
        .all()
    )
    avg_var_ratio = 0.6
    annual_op_est = 0
    if fin:
        rev = sum(f.revenue for f in fin)
        var = sum(f.raw_material_cost + f.labor_cost * 0.5 for f in fin)
        if rev:
            avg_var_ratio = min(0.95, max(0.3, var / rev))
        annual_op_est = sum(f.operating_profit for f in fin)

    # 1) 환율 → 수입 비용
    import_cost_up = p.annual_import_cost * p.fx_change_pct / 100

    # 2) 금리 → 금융 비용 (단순 이자 비용 근사)
    interest_up = p.debt_amount * p.rate_change_pct / 100

    # 3) 원자재 가격 → 제조원가
    material_up = company.annual_raw_material_cost * p.material_change_pct / 100

    # 4) 매출 감소 → 영업이익 (변동비 비례 차감 가정)
    annual_rev = company.annual_revenue or sum(f.revenue for f in fin) * 12 / max(1, len(fin))
    revenue_delta = annual_rev * p.revenue_change_pct / 100  # 음수 가능
    op_delta_from_rev = revenue_delta * (1 - avg_var_ratio)

    total_cost_up = import_cost_up + interest_up + material_up
    net_impact = -(total_cost_up) + op_delta_from_rev

    # 비용 상승만 있을 때 / 매출 하락만 있을 때 분리 표시
    cost_only = -(total_cost_up)
    rev_only = op_delta_from_rev

    grade, grade_reason = _severity(net_impact, annual_op_est or company.annual_revenue * 0.08)

    return {
        "params": p.model_dump(),
        "assumptions": {
            "변동비율_근사치": round(avg_var_ratio, 3),
            "변동비율_설명": "최근 12개월 원자재비+인건비 50%를 변동비로 근사",
            "연간_매출_기준": round(annual_rev),
            "연간_영업이익_추정": round(annual_op_est or 0),
            "시나리오_주의": "모든 계산은 '다른 조건이 동일하다'는 가정의 시나리오이며 실제 확정 손익이 아닙니다.",
        },
        "results": {
            "환율_상승에_따른_수입비용_증가": round(import_cost_up),
            "금리_상승에_따른_금융비용_증가": round(interest_up),
            "원자재가_상승에_따른_제조원가_증가": round(material_up),
            "매출_변동에_따른_영업이익_변동": round(op_delta_from_rev),
            "순_영향_추정": round(net_impact),
        },
        "formatted": {
            "환율_수입비용증가": fmt_krw(import_cost_up),
            "금융비용증가": fmt_krw(interest_up),
            "원자재원가증가": fmt_krw(material_up),
            "매출영업이익변동": fmt_krw(op_delta_from_rev),
            "순영향": fmt_krw(net_impact),
        },
        "severity": grade,
        "severity_reason": grade_reason,
        "severity_rules": "영업이익 대비 순영향 비율: <3% 정상 / 3~7% 관심 / 7~15% 주의 / 15~30% 위험 / ≥30% 심각",
        "calculation_example": (
            f"예) 연간 수입 비용 {fmt_krw(p.annual_import_cost)} × 환율 상승률 {p.fx_change_pct}% "
            f"= 약 {fmt_krw(import_cost_up)} 증가 (단순 가정 시나리오)"
        ),
    }
