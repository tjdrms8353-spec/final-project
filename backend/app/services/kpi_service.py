"""기업 내부 데이터 기반 경영 KPI 계산 서비스 (정식 전환 C).

설계 원칙 (지시서 §9):
- 수치 계산은 Python에서 수행하며 LLM에 맡기지 않는다.
- Decimal 기반 연산으로 부동소수점 오차를 억제한다 (입력이 Float 컬럼이라
  Decimal(str(v))로 변환해 계산한다).
- 데이터가 없는 경우 0으로 대체하지 않는다 — status로 구분한다.
  - "ok": 정상 계산
  - "insufficient_data": 입력 데이터가 없거나(NULL) 비교 기간 부족
  - "not_computable": 분모 0 등 수학적으로 계산 불가
- 각 지표에 계산식·기준·사용 데이터·비교 기간·단위·기준일을 포함한다.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import (
    Company, CustomerMonthly, FinancialMonthly, MaterialPurchase,
    ProductMonthly,
)

OK = "ok"
INSUFFICIENT = "insufficient_data"
NOT_COMPUTABLE = "not_computable"

# 화면 표시용 등급 경계 (문서 docs/ANALYSIS_MODEL.md와 동일 기준)


def _d(v) -> Decimal | None:
    """None/NaN을 None으로, 그 외는 Decimal로 변환한다."""
    if v is None:
        return None
    try:
        d = Decimal(str(v))
    except InvalidOperation:
        return None
    if d.is_nan():
        return None
    return d


def _kpi(key, name, value, unit, formula, data_used, basis,
         period, status=OK, note=""):
    """KPI 결과 dict. value는 float 또는 None."""
    return {
        "key": key, "name": name,
        "value": round(float(value), 2) if value is not None else None,
        "unit": unit, "formula": formula,
        "data_used": data_used,          # 사용한 입력 데이터 설명
        "basis": basis,                  # 계산 기준 (월별재무/누적 등)
        "period": period,                # 비교 기간
        "status": status,                # ok / insufficient_data / not_computable
        "note": note,                    # 데이터 부족 사유·계산 불가 사유
    }


def _div(num: Decimal | None, den: Decimal | None) -> tuple[Decimal | None, str]:
    """나눗셈. 반환 (결과|None, 상태). 분모 없음→insufficient, 0→not_computable."""
    if num is None or den is None:
        return None, INSUFFICIENT
    if den == 0:
        return None, NOT_COMPUTABLE
    return num / den, OK


def _growth(cur: Decimal | None, prev: Decimal | None) -> tuple[Decimal | None, str]:
    """증감률(%) = (당기-전기)/|전기|×100."""
    if cur is None or prev is None:
        return None, INSUFFICIENT
    if prev == 0:
        return None, NOT_COMPUTABLE
    return (cur - prev) / abs(prev) * 100, OK


def compute_kpi_report(db: Session, company_id: int) -> dict:
    """기업의 최신 월 기준 KPI 리포트를 반환한다.

    모든 월 데이터가 없으면 has_data=False와 빈 kpis를 반환한다.
    """
    fins = (
        db.query(FinancialMonthly)
        .filter(FinancialMonthly.company_id == company_id)
        .order_by(FinancialMonthly.month)
        .all()
    )
    company = db.get(Company, company_id)
    report = {
        "company_id": company_id,
        "generated_at": datetime.utcnow().isoformat(),
        "has_data": bool(fins),
        "basis_month": fins[-1].month if fins else "",
        "months_available": len(fins),
        "kpis": [],
        "product_profitability": [],
        "customer_dependence": {},
        "export_import": {},
        "insufficient_count": 0,
    }
    if not fins:
        report["kpis"] = [_kpi(
            "revenue", "매출액", None, "원",
            "월별 재무 데이터의 매출", "financial_monthly",
            "월별 재무 데이터", "-", INSUFFICIENT,
            "등록된 월별 재무 데이터가 없습니다. 데이터를 업로드하세요.")]
        report["insufficient_count"] = 1
        return report

    latest, prev = fins[-1], fins[-2] if len(fins) > 1 else None
    yoy = fins[-13] if len(fins) > 12 else None
    m = latest.month
    basis = "월별 재무 데이터 (financial_monthly)"
    K: list[dict] = []

    def add(*args, **kw):
        K.append(_kpi(*args, **kw))

    rev, op = _d(latest.revenue), _d(latest.operating_profit)
    ni = _d(latest.net_income)

    add("revenue", "매출액", rev, "원", "당월 매출",
        f"{m} 매출", basis, m)
    add("operating_profit", "영업이익", op, "원", "당월 영업이익",
        f"{m} 영업이익", basis, m)
    if ni is None:
        add("net_income", "순이익", None, "원", "당월 순이익",
            f"{m} 순이익", basis, m, INSUFFICIENT,
            "순이익 컬럼이 입력되지 않았습니다.")
    else:
        add("net_income", "순이익", ni, "원", "당월 순이익",
            f"{m} 순이익", basis, m)

    v, st = _div(op, rev)
    add("op_margin", "영업이익률", (v * 100) if v is not None else None, "%",
        "영업이익 ÷ 매출 × 100", f"{m} 영업이익·매출", basis, m, st,
        "매출이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else "")

    v, st = _div(ni, rev)
    add("net_margin", "순이익률", (v * 100) if v is not None else None, "%",
        "순이익 ÷ 매출 × 100", f"{m} 순이익·매출", basis, m, st,
        "순이익 미입력" if st == INSUFFICIENT else
        ("매출이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    v, st = _growth(rev, _d(prev.revenue) if prev else None)
    add("revenue_growth_mom", "매출 성장률(전월 대비)",
        v, "%", "(당월-전월) ÷ 전월 × 100",
        f"{m} 매출, {prev.month if prev else '전월'} 매출", basis,
        f"{prev.month if prev else '-'} → {m}", st,
        "전월 데이터가 없습니다." if st == INSUFFICIENT else
        ("전월 매출이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    v, st = _growth(rev, _d(yoy.revenue) if yoy else None)
    add("revenue_growth_yoy", "매출 성장률(전년동월 대비)",
        v, "%", "(당월-전년동월) ÷ 전년동월 × 100",
        f"{m} 매출, {yoy.month if yoy else '전년동월'} 매출", basis,
        f"{yoy.month if yoy else '-'} → {m}", st,
        "전년동월 데이터가 없습니다(13개월 이상 필요)." if st == INSUFFICIENT else
        ("전년동월 매출이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    def _cost(r):
        c = _d(r.raw_material_cost), _d(r.labor_cost), _d(r.other_cost)
        if any(x is None for x in c):
            return None
        return sum(c)

    v, st = _growth(_cost(latest), _cost(prev) if prev else None)
    add("cost_growth_mom", "비용 증가율(전월 대비)",
        v, "%", "(당월 비용합계-전월 비용합계) ÷ 전월 비용합계 × 100",
        "원자재비+인건비+기타비용", basis,
        f"{prev.month if prev else '-'} → {m}", st,
        "전월 데이터가 없습니다." if st == INSUFFICIENT else
        ("전월 비용이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    assets, liab = _d(latest.assets), _d(latest.liabilities)
    equity = (assets - liab) if (assets is not None and liab is not None) else None
    v, st = _div(liab, equity)
    add("debt_ratio", "부채비율", (v * 100) if v is not None else None, "%",
        "부채총계 ÷ 자본총계(자산-부채) × 100",
        f"{m} 자산총계·부채총계", basis, m, st,
        "자산/부채 미입력" if st == INSUFFICIENT else
        ("자본총계가 0(자산=부채)이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    ca, cl = _d(latest.current_assets), _d(latest.current_liabilities)
    v, st = _div(ca, cl)
    add("current_ratio", "유동비율", (v * 100) if v is not None else None, "%",
        "유동자산 ÷ 유동부채 × 100",
        f"{m} 유동자산·유동부채", basis, m, st,
        "유동자산/유동부채 미입력" if st == INSUFFICIENT else
        ("유동부채가 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    mfg = _d(latest.raw_material_cost)
    lab = _d(latest.labor_cost)
    mfg_cost = (mfg + lab) if (mfg is not None and lab is not None) else None
    add("manufacturing_cost", "제조원가(재료비+인건비)",
        mfg_cost, "원", "원자재비 + 인건비",
        f"{m} 원자재비·인건비", basis, m,
        OK if mfg_cost is not None else INSUFFICIENT,
        "" if mfg_cost is not None else "원자재비/인건비 미입력")

    add("raw_material_cost", "원자재 구매 비용", _d(latest.raw_material_cost), "원",
        "당월 원자재비", f"{m} 원자재비", basis, m)

    inv = _d(latest.inventory)
    v, st = _div(mfg_cost, inv)
    add("inventory_turnover", "재고 회전율(월)",
        v, "회", "제조원가 ÷ 재고자산",
        f"{m} 제조원가·재고자산", basis, m, st,
        "재고자산 미입력" if st == INSUFFICIENT else
        ("재고자산이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    exp, imp = _d(latest.export_amount), _d(latest.import_amount)
    v, st = _div(exp, rev)
    add("export_ratio", "수출 비중", (v * 100) if v is not None else None, "%",
        "수출액 ÷ 매출 × 100", f"{m} 수출액·매출", basis, m, st,
        "매출이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else "")
    cost_all = _cost(latest)
    v, st = _div(imp, cost_all)
    add("import_cost_ratio", "수입 비중(비용 대비)",
        (v * 100) if v is not None else None, "%",
        "수입액 ÷ 비용합계 × 100", f"{m} 수입액·비용합계", basis, m, st,
        "비용 데이터가 없습니다." if st == INSUFFICIENT else
        ("비용이 0이어서 계산할 수 없습니다." if st == NOT_COMPUTABLE else ""))

    # 외화 결제 비중 — 원자재 구매 통화 비중 우선, 없으면 프로필 값
    mats = (db.query(MaterialPurchase)
            .filter(MaterialPurchase.company_id == company_id,
                    MaterialPurchase.month == m).all())
    fx_ratio = None
    fx_basis = ""
    if mats:
        tot = sum(_d(x.amount_krw) or Decimal(0) for x in mats)
        fx = sum(_d(x.amount_krw) or Decimal(0)
                 for x in mats if (x.currency or "KRW").upper() != "KRW")
        if tot > 0:
            fx_ratio = float(fx / tot * 100)
            fx_basis = f"{m} 원자재 구매 통화 비중"
    if fx_ratio is None and company and company.fx_settlement_ratio:
        fx_ratio = float(_d(company.fx_settlement_ratio) * 100)
        fx_basis = "기업 프로필 외화 결제 비중"
    add("fx_settlement_ratio", "외화 결제 비중", fx_ratio, "%",
        "외화 구매액 ÷ 총 구매액 × 100 (또는 프로필 값)",
        fx_basis or "-", "원자재 구매 데이터 또는 기업 프로필", m,
        OK if fx_ratio is not None else INSUFFICIENT,
        "" if fx_ratio is not None else "구매 통화 데이터와 프로필 값이 모두 없습니다.")

    # ---- 부속 지표 ----
    report["kpis"] = K
    report["insufficient_count"] = sum(
        1 for k in K if k["status"] != OK)

    # 제품별 수익성 — 최근 월 기준 (수익률 = (매출-원가)/매출×100)
    prods = (db.query(ProductMonthly)
             .filter(ProductMonthly.company_id == company_id,
                     ProductMonthly.month == m).all())
    for p in prods:
        r, c = _d(p.revenue), _d(p.cost)
        v, st = _div((r - c) if (r is not None and c is not None) else None, r)
        report["product_profitability"].append({
            "product": p.product_name, "revenue": float(r or 0),
            "cost": float(c or 0),
            "margin_pct": round(float(v * 100), 2) if v is not None else None,
            "status": st,
        })

    # 거래처 의존도 — 최근 3개월 누적, 상위 1개 거래처 비중
    custs = (db.query(CustomerMonthly)
             .filter(CustomerMonthly.company_id == company_id)
             .order_by(CustomerMonthly.month.desc()).limit(500).all())
    if custs:
        recent = sorted({c.month for c in custs})[-3:]
        totals = {}
        for c in custs:
            if c.month in recent:
                totals[c.customer_name] = totals.get(c.customer_name, 0) + (
                    _d(c.revenue) or Decimal(0))
        total = sum(totals.values())
        if total > 0:
            top_name, top_val = max(totals.items(), key=lambda x: x[1])
            report["customer_dependence"] = {
                "top_customer": top_name,
                "share_pct": round(float(top_val / total * 100), 2),
                "period": f"{recent[0]}~{recent[-1]}",
                "status": OK,
            }
        else:
            report["customer_dependence"] = {"status": NOT_COMPUTABLE,
                                             "note": "거래처 매출 합계가 0입니다."}
    else:
        report["customer_dependence"] = {"status": INSUFFICIENT,
                                         "note": "거래처별 데이터가 없습니다."}

    report["export_import"] = {
        "export_amount": float(exp or 0), "import_amount": float(imp or 0),
        "export_countries": company.export_countries if company else "",
        "import_countries": company.import_countries if company else "",
    }
    return report
