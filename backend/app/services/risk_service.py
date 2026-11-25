"""기업 맞춤형 위험 평가 서비스 (정식 전환 C).

원칙 (지시서 §10·§15):
- 동일 외부 데이터라도 기업의 수출입 구조·프로필에 따라 평가가 달라진다.
  예) 환율 상승: 수입 중심 기업은 원가 상승 위험, 수출 중심 기업은
  환율 하락이 위험이며 상승은 오히려 우호적(헤지 여부에 따라 달라짐).
- 데이터 부족은 '위험 없음(정상)'이 아니라 '판단 보류'로 표시한다.
- 모든 판정에 근거 수치·계산 기준을 첨부한다. 등급 기준은
  docs/ANALYSIS_MODEL.md와 동일하게 유지한다.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import (
    Company, CustomerMonthly, FinancialMonthly, MarketSeries,
)
from ..utils import company_or_common

GRADES = ["정상", "관심", "주의", "위험", "심각"]
HOLD = "판단 보류"


def _grade(score: float) -> str:
    """점수(0~100) → 등급. 문서화 기준: docs/ANALYSIS_MODEL.md."""
    if score >= 80:
        return "심각"
    if score >= 60:
        return "위험"
    if score >= 40:
        return "주의"
    if score >= 20:
        return "관심"
    return "정상"


def _latest_two(series_rows):
    return (series_rows[-1].value, series_rows[-2].value) if len(series_rows) >= 2 \
        else (None, None)


def _series(db, company_id, key):
    return (db.query(MarketSeries)
            .filter(company_or_common(MarketSeries.company_id, company_id),
                    MarketSeries.series_key == key)
            .order_by(MarketSeries.month).all())


def _item(category, score, evidence, basis, sufficient=True, note=""):
    return {
        "category": category,
        "score": round(score, 1) if sufficient and score is not None else None,
        "grade": _grade(score) if sufficient and score is not None else HOLD,
        "data_sufficient": sufficient and score is not None,
        "evidence": evidence if sufficient else "",
        "basis": basis,
        "note": note if not sufficient else note,
    }


def assess_risks(db: Session, company_id: int) -> dict:
    """기업 맞춤 위험 프로필 — 카테고리별 점수·등급·근거를 반환한다."""
    company = db.get(Company, company_id)
    fins = (db.query(FinancialMonthly)
            .filter(FinancialMonthly.company_id == company_id)
            .order_by(FinancialMonthly.month).all())
    latest = fins[-1] if fins else None

    # 기업 수출입 구조 추정 — 실데이터 우선, 프로필 보조
    export_amt = latest.export_amount if latest else 0
    import_amt = latest.import_amount if latest else 0
    revenue = latest.revenue if latest else 0
    if export_amt or import_amt:
        trade_dir = ("export" if export_amt > import_amt * 1.2 else
                     "import" if import_amt > export_amt * 1.2 else "balanced")
    else:
        ei = (company.export_import_ratio or "") if company else ""
        trade_dir = ("export" if ei.startswith("수출") else
                     "import" if ei.startswith("수입") else "unknown")
    context = {
        "trade_direction": trade_dir,   # export/import/balanced/unknown
        "export_amount": export_amt, "import_amount": import_amt,
        "fx_settlement_ratio": company.fx_settlement_ratio if company else 0,
        "industry": company.industry if company else "",
        "export_countries": company.export_countries if company else "",
        "import_countries": company.import_countries if company else "",
        "raw_materials": company.raw_materials if company else "",
    }

    items = []

    # 1) 환율 위험 — 수출입 구조에 따라 방향이 다르다
    fx = _series(db, company_id, "USD_KRW")
    cur, prv = _latest_two(fx)
    if cur is None:
        items.append(_item("환율", None, "", "USD_KRW 시계열", False,
                           "환율 시계열 데이터가 없습니다(수집기 미설정·미수집)."))
    else:
        chg = (cur - prv) / prv * 100
        exposure = max(export_amt, import_amt) / revenue * 100 if revenue else 0
        if trade_dir == "import":
            # 원화 약세(환율 상승) → 수입 원가 상승 위험
            score = min(100, max(0, chg) * 15 + exposure * 0.5)
            ev = (f"환율 {chg:+.2f}%({prv:,.0f}→{cur:,.0f}원), 수입 중심 기업 — "
                  f"환율 상승 시 수입 원가 상승. 비용 대비 수입 비중 {exposure:.0f}%")
            note = "환헤지 여부·계약 결제 통화에 따라 실제 영향은 달라집니다."
        elif trade_dir == "export":
            # 원화 강세(환율 하락) → 외화 매출 원화 환산액 감소 위험
            score = min(100, max(0, -chg) * 15 + exposure * 0.5)
            ev = (f"환율 {chg:+.2f}%({prv:,.0f}→{cur:,.0f}원), 수출 중심 기업 — "
                  f"환율 하락 시 외화 매출의 원화 환산액 감소. 매출 대비 수출 비중 {exposure:.0f}%")
            note = "환율 상승은 외화 매출에 우호적이나 헤지 여부에 따라 달라집니다."
        else:
            score = min(100, abs(chg) * 15 + exposure * 0.5)
            ev = (f"환율 {chg:+.2f}%, 수출입 구조 불명확 — "
                  "변동성 자체를 위험으로 평가합니다.")
            note = "수출입 구조 데이터를 입력하면 방향성 있는 평가가 가능합니다."
        items.append(_item("환율", score, ev, "USD_KRW 시계열 + 기업 수출입 구조",
                           True, note))

    # 2) 금리 위험 — 차입금 규모와 금리 변화
    rate = _series(db, company_id, "BASE_RATE")
    cur, prv = _latest_two(rate)
    borrow = latest.borrowings if latest else None
    if cur is None:
        items.append(_item("금리", None, "", "BASE_RATE 시계열", False,
                           "기준금리 시계열 데이터가 없습니다."))
    else:
        chg = cur - prv
        debt_ratio = (borrow / revenue * 100) if (borrow and revenue) else None
        score = min(100, max(0, chg) * 40 + (debt_ratio or 0) * 0.3)
        ev = (f"기준금리 {chg:+.2f}%p({prv}→{cur}%), "
              + (f"차입금/월매출 {debt_ratio:.0f}%" if debt_ratio is not None
                 else "차입금 미입력 — 금리 민감도 정량 평가 불가"))
        items.append(_item("금리", score, ev,
                           "BASE_RATE 시계열 + 차입금",
                           True,
                           "차입금 미입력으로 금리 영향이 과소평가될 수 있습니다."
                           if debt_ratio is None else ""))

    # 3) 원자재 가격 위험 — 원자재 비용 비중 + 유가 시계열
    if latest and revenue:
        rm_ratio = latest.raw_material_cost / revenue * 100
        wti = _series(db, company_id, "WTI_OIL")
        wcur, wprv = _latest_two(wti)
        wchg = ((wcur - wprv) / wprv * 100) if wcur and wprv else 0
        score = min(100, rm_ratio * 0.8 + max(0, wchg) * 5)
        ev = (f"매출 대비 원자재 비용 비중 {rm_ratio:.0f}%"
              + (f", WTI 유가 {wchg:+.1f}%" if wcur else ", 유가 시계열 없음"))
        items.append(_item("원자재 가격", score, ev,
                           "원자재비/매출 + WTI_OIL 시계열", True))
    else:
        items.append(_item("원자재 가격", None, "", "월별 재무 데이터", False,
                           "원자재비 또는 매출 데이터가 없습니다."))

    # 4) 수익성 악화 — 영업이익률 추이
    if len(fins) >= 2 and revenue:
        margin = latest.operating_profit / revenue * 100
        pr = fins[-2]
        pm = (pr.operating_profit / pr.revenue * 100) if pr.revenue else None
        drop = (pm - margin) if pm is not None else 0
        score = min(100, max(0, drop) * 12 + max(0, -margin) * 3)
        ev = (f"영업이익률 {margin:.1f}%"
              + (f" (전월 {pm:.1f}% 대비 {-drop:+.1f}%p)" if pm is not None else ""))
        items.append(_item("수익성", score, ev, "영업이익률 전월 대비", True))
    else:
        items.append(_item("수익성", None, "", "월별 재무 데이터", False,
                           "2개월 이상의 재무 데이터가 필요합니다."))

    # 5) 매출 감소 — 전년동월·전월 대비
    yoy = fins[-13] if len(fins) > 12 else None
    if yoy and yoy.revenue and revenue:
        g = (revenue - yoy.revenue) / yoy.revenue * 100
        score = min(100, max(0, -g) * 8)
        items.append(_item("매출", score,
                           f"매출 전년동월 대비 {g:+.1f}% ({yoy.month}→{latest.month})",
                           "월별 재무 데이터", True))
    elif len(fins) >= 2 and fins[-2].revenue and revenue:
        g = (revenue - fins[-2].revenue) / fins[-2].revenue * 100
        score = min(100, max(0, -g) * 8)
        items.append(_item("매출", score,
                           f"매출 전월 대비 {g:+.1f}% (전년동월 데이터 없어 전월 기준)",
                           "월별 재무 데이터", True,
                           "13개월 이상 데이터 시 전년동월 비교로 정확도가 높아집니다."))
    else:
        items.append(_item("매출", None, "", "월별 재무 데이터", False,
                           "비교 가능한 매출 데이터가 없습니다."))

    # 6) 거래처 집중 위험 — 상위 거래처 비중
    custs = (db.query(CustomerMonthly)
             .filter(CustomerMonthly.company_id == company_id)
             .order_by(CustomerMonthly.month.desc()).limit(500).all())
    if custs:
        recent = sorted({c.month for c in custs})[-3:]
        totals = {}
        for c in custs:
            if c.month in recent:
                totals[c.customer_name] = totals.get(c.customer_name, 0) + c.revenue
        total = sum(totals.values())
        if total > 0:
            name, val = max(totals.items(), key=lambda x: x[1])
            share = val / total * 100
            items.append(_item("거래처 집중", min(100, share * 1.5),
                               f"최대 거래처 '{name}' 매출 비중 {share:.0f}%",
                               "거래처별 최근 3개월 매출", True))
        else:
            items.append(_item("거래처 집중", None, "", "거래처별 데이터", False,
                               "거래처 매출 합계가 0입니다."))
    else:
        items.append(_item("거래처 집중", None, "", "거래처별 데이터", False,
                           "거래처별 매출 데이터가 없습니다."))

    # 7) 재고 부담 — 재고자산/월매출 비율
    if latest and latest.inventory is not None and revenue:
        inv_ratio = latest.inventory / revenue * 100
        items.append(_item("재고 부담", min(100, inv_ratio * 0.8),
                           f"재고자산 {latest.inventory:,.0f}원 = 월매출의 {inv_ratio:.0f}%",
                           "재고자산/월매출", True))
    else:
        items.append(_item("재고 부담", None, "", "재고자산", False,
                           "재고자산 또는 매출 데이터가 없습니다."))

    # 8) 재무 안정성 — 부채비율·유동비율
    if latest and latest.assets is not None and latest.liabilities is not None:
        equity = latest.assets - latest.liabilities
        dr = (latest.liabilities / equity * 100) if equity > 0 else None
        if dr is None:
            items.append(_item("재무 안정성", 100,
                               f"자본총계가 0 이하(자산 {latest.assets:,.0f}원 ≤ 부채 {latest.liabilities:,.0f}원)",
                               "부채총계/자본총계", True))
        else:
            score = min(100, max(0, dr - 100) * 0.4)  # 부채비율 100% 초과분 위험
            ev = f"부채비율 {dr:.0f}%"
            if latest.current_assets is not None and latest.current_liabilities:
                cr = latest.current_assets / latest.current_liabilities * 100
                score = min(100, score + max(0, 100 - cr) * 0.4)
                ev += f", 유동비율 {cr:.0f}%"
            items.append(_item("재무 안정성", score, ev,
                               "부채비율·유동비율", True))
    else:
        items.append(_item("재무 안정성", None, "", "자산/부채", False,
                           "자산·부채 데이터가 없습니다."))

    # 종합 — 계산 가능한 항목만 평균, 데이터 부족 비율도 함께 표시
    scored = [i for i in items if i["data_sufficient"]]
    overall = sum(i["score"] for i in scored) / len(scored) if scored else None
    worst = max(scored, key=lambda i: i["score"]) if scored else None
    return {
        "company_id": company_id,
        "assessed_at": datetime.utcnow().isoformat(),
        "company_context": context,
        "items": items,
        "overall_score": round(overall, 1) if overall is not None else None,
        "overall_grade": (_grade(overall) if overall is not None else HOLD),
        "top_risk": worst["category"] if worst else "",
        "insufficient_count": len(items) - len(scored),
        "note": ("데이터 부족 항목은 '판단 보류'이며 '정상'이 아닙니다. "
                 "최종 판단은 관리자가 수행해야 합니다."),
    }
