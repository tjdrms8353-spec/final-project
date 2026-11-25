"""
규칙 기반 데모 분석 엔진.

실제 LLM이 연결되지 않은 데모 환경에서 동작하는 투명한 규칙 기반 분석기다.
모든 분석 결과에는 '데모 분석'임을 명시하고, 계산 근거와 사용 데이터를 함께 제공한다.
향후 LLM 연동 시 이 모듈을 대체할 수 있도록 compute_kpis/run_analysis 인터페이스를 유지한다.
"""
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import (
    AnalysisResult, Company, CustomerMonthly, FinancialMonthly, MarketSeries,
    NewsItem, Notification, NotificationSetting, ProductMonthly, RiskAlert,
)
from ..utils import company_or_common, fmt_krw, month_range, prev_month

DEMO_DISCLAIMER = (
    "본 분석은 실제 AI/LLM이 아닌 규칙 기반 데모 분석 엔진의 결과입니다. "
    "수치는 등록된 데모 데이터와 외부 지표(데모 생성)만을 근거로 하며, "
    "투자·경영 의사결정의 최종 판단은 반드시 관리자가 직접 수행해야 합니다."
)

# 위험 등급 판단 기준 (서비스 화면에도 동일하게 표시)
SEVERITY_RULES = {
    "fx": [
        ("심각", 6.0), ("위험", 4.0), ("주의", 2.0),
    ],
    "op_margin_drop": [  # 전년동월 대비 영업이익률 하락폭(%p)
        ("위험", 4.0), ("주의", 2.0),
    ],
    "revenue_yoy": [  # 매출 전년동기 대비 성장률(%), 낮을수록 위험
        ("위험", -5.0), ("주의", -2.0),
    ],
    "material_ratio": [  # 원자재비 / 매출 (%)
        ("주의", 62.0),
    ],
}


def _series(db: Session, company_id: int, model, order_field="month"):
    return (
        db.query(model)
        .filter(model.company_id == company_id)
        .order_by(getattr(model, order_field))
        .all()
    )


def compute_kpis(db: Session, company_id: int) -> dict:
    fin = _series(db, company_id, FinancialMonthly)
    if not fin:
        return {"has_data": False}

    latest = fin[-1]
    prev = fin[-2] if len(fin) > 1 else None
    yoy = fin[-13] if len(fin) > 12 else None

    def pct(new, old):
        if not old:
            return None
        return round((new - old) / abs(old) * 100, 2)

    revenue = latest.revenue
    op = latest.operating_profit
    kpis = {
        "has_data": True,
        "month": latest.month,
        "revenue": revenue,
        "operating_profit": op,
        "op_margin": round(op / revenue * 100, 2) if revenue else 0,
        "revenue_mom": pct(revenue, prev.revenue if prev else None),
        "revenue_yoy": pct(revenue, yoy.revenue if yoy else None),
        "op_mom": pct(op, prev.operating_profit if prev else None),
        "op_yoy": pct(op, yoy.operating_profit if yoy else None),
        "op_margin_yoy": round(
            (op / revenue * 100) - (yoy.operating_profit / yoy.revenue * 100), 2
        ) if yoy and yoy.revenue and revenue else None,
        "raw_material_ratio": round(latest.raw_material_cost / revenue * 100, 1) if revenue else 0,
        "labor_ratio": round(latest.labor_cost / revenue * 100, 1) if revenue else 0,
        "other_ratio": round(latest.other_cost / revenue * 100, 1) if revenue else 0,
        "fx_avg_rate": latest.fx_avg_rate,
        "fx_mom_pct": pct(latest.fx_avg_rate, prev.fx_avg_rate if prev else None),
        "export_ratio": round(latest.export_amount / revenue * 100, 1) if revenue else 0,
        "months": len(fin),
    }

    # 환율 시계열 최신/이전 (공통 데이터 + 기업 전용 데이터)
    fx = (
        db.query(MarketSeries)
        .filter(company_or_common(MarketSeries.company_id, company_id),
                MarketSeries.series_key == "USD_KRW")
        .order_by(MarketSeries.month)
        .all()
    )
    if len(fx) >= 2:
        kpis["fx_latest"] = fx[-1].value
        kpis["fx_prev"] = fx[-2].value
        kpis["fx_mom_pct_series"] = round((fx[-1].value - fx[-2].value) / fx[-2].value * 100, 2)

    # 고객 집중도 (최근 3개월 평균)
    cust = (
        db.query(CustomerMonthly)
        .filter(CustomerMonthly.company_id == company_id)
        .order_by(CustomerMonthly.month.desc())
        .limit(500)
        .all()
    )
    if cust:
        recent_months = sorted({c.month for c in cust})[-3:]
        totals = {}
        for c in cust:
            if c.month in recent_months:
                totals[c.customer_name] = totals.get(c.customer_name, 0) + c.revenue
        total = sum(totals.values())
        if total:
            top = sorted(totals.items(), key=lambda x: -x[1])
            kpis["customer_concentration"] = [
                {"name": n, "share": round(v / total * 100, 1)} for n, v in top[:5]
            ]
            kpis["top1_customer_share"] = round(top[0][1] / total * 100, 1)

    # 제품별 수익률 (최근 3개월)
    prod = _series(db, company_id, ProductMonthly)
    if prod:
        recent = [p for p in prod if p.month in month_range(3)]
        agg = {}
        for p in recent:
            a = agg.setdefault(p.product_name, {"revenue": 0, "cost": 0})
            a["revenue"] += p.revenue
            a["cost"] += p.cost
        kpis["product_margin"] = [
            {
                "name": n,
                "revenue": v["revenue"],
                "margin": round((v["revenue"] - v["cost"]) / v["revenue"] * 100, 1) if v["revenue"] else 0,
            }
            for n, v in sorted(agg.items(), key=lambda x: -x[1]["revenue"])
        ]

    # 주요 뉴스 sentiment 집계 (공통 수집 뉴스 + 기업 전용 뉴스)
    news = (
        db.query(NewsItem)
        .filter(company_or_common(NewsItem.company_id, company_id))
        .order_by(NewsItem.published_at.desc())
        .limit(30)
        .all()
    )
    kpis["recent_news_count"] = len(news)
    kpis["negative_news_count"] = sum(1 for n in news if n.sentiment == "negative")
    return kpis


def _mk_analysis(db, company_id, analysis_type, title, summary, details,
                 sources, impact, uncertainty, suggestions, trigger):
    a = AnalysisResult(
        company_id=company_id,
        analysis_type=analysis_type,
        title=title,
        summary=summary,
        details=details,
        data_sources=sources,
        basis_date=datetime.utcnow().strftime("%Y-%m-%d"),
        impact=impact,
        uncertainty=uncertainty,
        suggestions=suggestions,
        engine="rule-based-demo",
        trigger=trigger,
    )
    db.add(a)
    return a


def _mk_alert(db, company_id, severity, category, title, message, related_type="", related_id=None):
    # 동일 제목의 미해결 알림이 최근 7일 내 있으면 중복 생성하지 않음
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=7)
    dup = (
        db.query(RiskAlert)
        .filter(RiskAlert.company_id == company_id, RiskAlert.title == title,
                RiskAlert.status != "acknowledged", RiskAlert.created_at >= cutoff)
        .first()
    )
    if dup:
        return None
    a = RiskAlert(
        company_id=company_id, severity=severity, category=category,
        title=title, message=message, related_type=related_type, related_id=related_id,
    )
    db.add(a)
    return a


def _mk_notification(db, company_id, ntype, title, message):
    n = Notification(company_id=company_id, ntype=ntype, title=title, message=message)
    db.add(n)
    return n


def _queue_email_if_enabled(db, company_id, title, message):
    st = db.query(NotificationSetting).filter(NotificationSetting.company_id == company_id).first()
    if st and st.email_enabled:
        _mk_notification(db, company_id, "email",
                         f"[발송 대기] {title}",
                         f"{message}\n\n※ 외부 발송 API 미연결 데모: 실제 이메일은 발송되지 않고 대기 상태로 기록됩니다.")


def _setting(db, company_id, flag: str) -> bool:
    """알림 설정 플래그 조회. 설정 행이 없으면 기본값(True)을 쓴다."""
    st = db.query(NotificationSetting).filter(
        NotificationSetting.company_id == company_id).first()
    return getattr(st, flag, True) if st else True


def detect_risks(db: Session, company_id: int, trigger: str = "auto") -> list[RiskAlert]:
    """임계값 기반 위험 감지. 새 알림과 알림(Notification)을 생성한다."""
    kpis = compute_kpis(db, company_id)
    if not kpis.get("has_data"):
        return []
    company = db.get(Company, company_id)
    created = []

    # 1) 환율 위험 — 외화 결제 비중을 감안해 등급 보정
    fx_pct = kpis.get("fx_mom_pct_series") or kpis.get("fx_mom_pct") or 0
    if fx_pct > 0:
        threshold_shift = -1 if (company and company.fx_settlement_ratio >= 0.5) else 0
        grade = "정상"
        for name, th in SEVERITY_RULES["fx"]:
            if fx_pct >= th + threshold_shift * 0.5:
                grade = name
                break
        if grade != "정상":
            impact_amt = company.annual_raw_material_cost * company.fx_settlement_ratio * fx_pct / 100 if company else 0
            a = _mk_alert(
                db, company_id, grade, "환율",
                f"원/달러 환율 급등 ({fx_pct:+.1f}%)",
                f"최근 1개월 원/달러 환율이 {fx_pct:+.1f}% 변동했습니다. "
                f"외화 결제 비중 {company.fx_settlement_ratio*100:.0f}% 기준 단순 환산 시 "
                f"연간 수입 비용이 약 {fmt_krw(impact_amt)} 증가할 수 있습니다(조건 동일 가정의 시나리오).",
            )
            if a:
                created.append(a)
                if _setting(db, company_id, "risk_alert"):
                    _mk_notification(db, company_id, "risk",
                                     f"위험 알림: {a.title}", a.message)
                    _queue_email_if_enabled(db, company_id, a.title, a.message)

    # 2) 영업이익률 전년동월 대비 하락
    drop = -(kpis.get("op_margin_yoy") or 0)
    if drop >= 2.0:
        grade = "위험" if drop >= 4.0 else "주의"
        a = _mk_alert(
            db, company_id, grade, "수익성",
            f"영업이익률 전년동월 대비 {drop:.1f}%p 하락",
            f"최근 월 영업이익률 {kpis['op_margin']}%로 전년동월 대비 {kpis['op_margin_yoy']:+.1f}%p 변동했습니다. "
            f"원자재 비용 비중({kpis['raw_material_ratio']}%)과 제품별 수익률을 점검하세요.",
        )
        if a:
            created.append(a)
            if _setting(db, company_id, "risk_alert"):
                _mk_notification(db, company_id, "risk", f"위험 알림: {a.title}", a.message)

    # 3) 매출 전년동기 감소
    yoy = kpis.get("revenue_yoy") or 0
    if yoy < -2.0:
        grade = "위험" if yoy < -5.0 else "주의"
        a = _mk_alert(
            db, company_id, grade, "매출",
            f"매출 전년동기 대비 {yoy:+.1f}% 감소",
            f"최근 월 매출 {fmt_krw(kpis['revenue'])}로 전년동기 대비 {yoy:+.1f}%입니다. "
            f"주요 거래처별 매출과 산업 수요 지표를 함께 확인하세요.",
        )
        if a:
            created.append(a)
            if _setting(db, company_id, "risk_alert"):
                _mk_notification(db, company_id, "risk", f"위험 알림: {a.title}", a.message)

    # 4) 원자재 비용 비중
    if kpis.get("raw_material_ratio", 0) >= 62.0:
        a = _mk_alert(
            db, company_id, "주의", "원가",
            f"원자재 비용 비중 {kpis['raw_material_ratio']}%로 상승",
            "매출 대비 원자재 구매 비용 비중이 높습니다. 원자재 가격 추이와 장기 공급 계약 조건을 검토하세요.",
        )
        if a:
            created.append(a)

    # 5) 고객 집중도
    if kpis.get("top1_customer_share", 0) >= 40.0:
        a = _mk_alert(
            db, company_id, "관심", "거래처",
            f"최대 거래처 매출 의존도 {kpis['top1_customer_share']}%",
            "특정 거래처에 매출이 집중되어 있습니다. 해당 거래처의 수요 변동이 실적에 직접 영향을 줍니다.",
        )
        if a:
            created.append(a)

    # 6) 부정적 중요 뉴스 — 기업 전용은 NewsItem.importance, 공통 뉴스는 기업별 점수 사용
    from ..models import CompanyNewsScore as _CNS
    neg = (
        db.query(NewsItem)
        .outerjoin(_CNS, (_CNS.news_item_id == NewsItem.id)
                   & (_CNS.company_id == company_id))
        .filter(NewsItem.sentiment == "negative")
        .filter(or_(
            (NewsItem.company_id == company_id) & (NewsItem.importance == "높음"),
            (NewsItem.company_id.is_(None)) & (_CNS.importance == "높음"),
        ))
        .order_by(NewsItem.published_at.desc())
        .first()
    )
    if neg:
        a = _mk_alert(
            db, company_id, "관심", "뉴스",
            f"부정적 산업 뉴스: {neg.title[:60]}",
            f"관련성 {neg.relevance_score}점의 부정적 뉴스가 등록되었습니다. {neg.impact_on_company}",
        )
        if a:
            created.append(a)
            if _setting(db, company_id, "important_news"):
                _mk_notification(db, company_id, "news", f"중요 뉴스: {neg.title[:60]}", neg.summary[:200])

    return created


def run_analyses(db: Session, company_id: int, trigger: str = "manual") -> list[AnalysisResult]:
    """성장/방향성/위험 3개 영역의 분석 결과를 생성한다."""
    kpis = compute_kpis(db, company_id)
    company = db.get(Company, company_id)
    created = []
    if not kpis.get("has_data") or not company:
        return created

    month = kpis["month"]
    src = f"내부 재무 데이터({kpis['months']}개월), 시장 시계열(데모), 뉴스 {kpis['recent_news_count']}건"
    basis = {
        "metrics": {
            "매출": fmt_krw(kpis["revenue"]),
            "영업이익": fmt_krw(kpis["operating_profit"]),
            "영업이익률": f"{kpis['op_margin']}%",
            "매출 전년동기": f"{kpis['revenue_yoy']:+.1f}%" if kpis["revenue_yoy"] is not None else "-",
            "영업이익률 전년동월": f"{kpis['op_margin_yoy']:+.1f}%p" if kpis.get("op_margin_yoy") is not None else "-",
            "원자재비 비중": f"{kpis['raw_material_ratio']}%",
            "원/달러 환율": f"{kpis.get('fx_latest', kpis['fx_avg_rate']):.1f}원",
        },
        "disclaimer": DEMO_DISCLAIMER,
    }

    # A. 미래 성장 가능성
    yoy = kpis.get("revenue_yoy") or 0
    if yoy > 3:
        g_title = "성장세 유지 — 수출 비중 확대가 견인"
        g_sum = f"최근 매출이 전년동기 대비 {yoy:+.1f}% 증가했습니다. 수출 비중 {kpis['export_ratio']}% 환경에서 주요 시장 수요가 유지되고 있습니다."
        g_sug = "주요 수출 국가별 분기별 수요 모니터링과 신규 모델 수주 파이프라인 점검을 권장합니다."
    elif yoy > -2:
        g_title = "성장 정체 구간 — 회복 동력 확인 필요"
        g_sum = f"매출 전년동기 {yoy:+.1f}%로 정체 상태입니다. 성장 동력별(제품/거래처) 기여도를 분해해 확인이 필요합니다."
        g_sug = "제품별 수익률 하위 품목의 원가 구조와 거래처 다변화 여지를 검토하세요."
    else:
        g_title = "성장 둔화 우려 — 수요·수주 지표 점검 필요"
        g_sum = f"매출 전년동기 {yoy:+.1f}% 감소했습니다. 산업 수요 둔화 또는 특정 거래처 수주 감소 가능성이 있습니다."
        g_sug = "주요 거래처 수주 계획과 반도체 산업 선행지표(재고/설비투자)를 확인하세요."
    created.append(_mk_analysis(
        db, company_id, "growth", g_title, g_sum, basis, src,
        "성장 지속 시 매출 확대, 둔화 시 설비투자·인력 계획 재검토 필요",
        "24개월 데모 데이터 기반이며 외부 산업 전망 데이터는 제한적입니다. 계절성·일회성 수주가 반영되지 않았을 수 있습니다.",
        g_sug, trigger))

    # B. 사업 방향성
    worst = min(kpis.get("product_margin", [{"margin": 0, "name": "-"}]), key=lambda x: x["margin"])
    d_title = "원가 구조와 제품 믹스 중심의 방향성 검토"
    d_sum = (
        f"원자재 비용 비중 {kpis['raw_material_ratio']}%, 인건비 비중 {kpis['labor_ratio']}%입니다. "
        f"수익률 최하위 제품은 '{worst['name']}'({worst['margin']}%)입니다."
    )
    d_sug = (
        "원자재 장기공급계약 비중 확대, 최하위 수익률 제품의 단가·원가 재검토, "
        "수출 비중이 높은 만큼 환헤지 정책 수립을 검토하세요."
    )
    created.append(_mk_analysis(
        db, company_id, "direction", d_title, d_sum, basis, src,
        "원가 절감·제품 믹스 개선 시 영업이익률 개선 여지 존재",
        "제품별 데이터가 월 단위 집계라 세부 원인(단가/수율/ Mix) 분리는 제한됩니다.",
        d_sug, trigger))

    # C. 위험 요소 관리 — 감지된 위험을 종합
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.company_id == company_id, RiskAlert.status != "acknowledged")
        .order_by(RiskAlert.created_at.desc())
        .limit(10)
        .all()
    )
    top = alerts[0] if alerts else None
    r_title = "위험 요인 종합 점검 — 우선순위 기반 대응 필요"
    if alerts:
        r_sum = "미해결 위험 알림 " + str(len(alerts)) + "건이 있습니다. " + "; ".join(
            f"[{a.severity}] {a.title}" for a in alerts[:3])
    else:
        r_sum = "현재 감지된 주요 위험 알림이 없습니다. KPI와 시장 지표는 정상 범위입니다."
    r_sug = "위험 영향 시뮬레이션 메뉴에서 환율·금리·원자재 변동 시나리오를 직접 계산해 보세요."
    created.append(_mk_analysis(
        db, company_id, "risk", r_title, r_sum,
        {**basis, "active_alerts": [{"severity": a.severity, "title": a.title} for a in alerts]},
        src,
        "상위 위험의 방치 시 수익성·현금흐름 악화 가능",
        "위험 등급은 설정된 임계값 기반이며 실제 손실 확정이 아닙니다.",
        r_sug, trigger))

    # KPI 변동 알림
    if kpis.get("op_mom") is not None and abs(kpis["op_mom"]) >= 10:
        if _setting(db, company_id, "kpi_change"):
            _mk_notification(db, company_id, "kpi",
                             f"경영지표 변동: 영업이익 전월 대비 {kpis['op_mom']:+.1f}%",
                             f"{month} 영업이익이 전월 대비 {kpis['op_mom']:+.1f}% 변동했습니다.")

    return created


def _data_signature(db: Session, company_id: int) -> str:
    """분석 입력 데이터 서명 — 동일 데이터의 중복 분석 방지용.

    건수가 아닌 '내용'을 해시한다 — 같은 월이라도 값이 바뀌면
    서명이 달라져 재분석이 실행되고, 정말 동일한 데이터만 건너뛴다.
    """
    import hashlib

    def md5(rows, fmt):
        s = "|".join(fmt(r) for r in rows)
        return hashlib.md5(s.encode()).hexdigest()[:12]

    fins = (db.query(FinancialMonthly)
            .filter(FinancialMonthly.company_id == company_id)
            .order_by(FinancialMonthly.month).all())
    fin_sig = md5(fins, lambda r: (
        f"{r.month},{r.revenue},{r.operating_profit},{r.raw_material_cost},"
        f"{r.labor_cost},{r.other_cost},{r.export_amount},{r.import_amount},"
        f"{r.fx_avg_rate},{r.net_income},{r.assets},{r.liabilities},"
        f"{r.inventory},{r.borrowings},{r.current_assets},{r.current_liabilities}"))

    news = (db.query(NewsItem.id)
            .filter(company_or_common(NewsItem.company_id, company_id))
            .order_by(NewsItem.id).all())
    news_sig = md5(news, lambda r: str(r[0]))

    series = (db.query(MarketSeries)
              .filter(company_or_common(MarketSeries.company_id, company_id))
              .order_by(MarketSeries.series_key, MarketSeries.month).all())
    series_sig = md5(series, lambda r: f"{r.series_key},{r.month},{r.value}")
    return f"f{fin_sig}:n{news_sig}:s{series_sig}"


def run_pipeline(db: Session, company_id: int, trigger: str = "manual",
                 force: bool = False) -> dict:
    """자동 분석 파이프라인: KPI 계산 → 위험 감지 → 분석 생성 → 알림 → 이력 저장.

    동일 입력 데이터(서명)에 대해 같은 트리거로 이미 완료된 작업이 있으면
    중복 분석을 건너뛴다. force=True면 무시하고 실행한다(수동 실행).
    작업 이력은 analysis_jobs에 기록된다.
    """
    from ..models import AnalysisJob

    sig = _data_signature(db, company_id)
    dedup_key = f"{trigger}:{sig}"
    if not force:
        dup = (db.query(AnalysisJob)
               .filter(AnalysisJob.company_id == company_id,
                       AnalysisJob.dedup_key == dedup_key,
                       AnalysisJob.status == "done")
               .first())
        if dup:
            return {"trigger": trigger, "skipped": "duplicate",
                    "ran_at": datetime.utcnow().isoformat(),
                    "new_alerts": 0, "new_analyses": 0, "alert_titles": []}

    job = AnalysisJob(company_id=company_id, trigger=trigger,
                      dedup_key=dedup_key, status="running")
    db.add(job)
    db.flush()
    try:
        alerts = detect_risks(db, company_id, trigger)
        # LLM 설정 시 LLM 우선, 미설정·실패 시 규칙 기반 엔진 폴백 (지연 import로 순환 참조 방지)
        from .llm_provider import run_analysis as provider_run_analysis
        analyses = provider_run_analysis(db, company_id, trigger)

        # "분석 완료" 알림 (설정이 켜져 있을 때만)
        if analyses and _setting(db, company_id, "analysis_done"):
            _mk_notification(
                db, company_id, "analysis",
                f"경영 분석 완료 ({len(analyses)}건)",
                "새 분석 결과: " + "; ".join(a.title for a in analyses)
                + " — AI 분석 메뉴에서 근거·불확실성을 확인하세요.")

        job.status = "done"
        job.result_count = len(analyses)
        job.finished_at = datetime.utcnow()
    except Exception as e:
        job.status = "failed"
        job.error = str(e)[:1900]
        job.finished_at = datetime.utcnow()
        db.commit()
        raise

    return {
        "trigger": trigger,
        "ran_at": datetime.utcnow().isoformat(),
        "new_alerts": len(alerts),
        "new_analyses": len(analyses),
        "alert_titles": [a.title for a in alerts],
    }


def weekly_summary(db: Session, company_id: int) -> Notification | None:
    """주간 요약 알림 생성. 설정이 꺼져 있으면 발행하지 않는다.

    최근 7일 동안의 미해결 위험 알림·생성된 분석·읽지 않은 알림을 요약한다.
    같은 주에 이미 발행된 주간 요약이 있으면 중복 생성하지 않는다.
    """
    from datetime import timedelta
    from ..models import AnalysisResult as _AR

    if not _setting(db, company_id, "weekly_summary"):
        return None

    cutoff = datetime.utcnow() - timedelta(days=7)
    dup = (
        db.query(Notification)
        .filter(Notification.company_id == company_id,
                Notification.ntype == "weekly",
                Notification.created_at >= cutoff)
        .first()
    )
    if dup:
        return None

    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.company_id == company_id,
                RiskAlert.status != "acknowledged")
        .order_by(RiskAlert.created_at.desc()).all()
    )
    analyses = (
        db.query(_AR)
        .filter(_AR.company_id == company_id, _AR.created_at >= cutoff)
        .count()
    )
    unread = (
        db.query(Notification)
        .filter(Notification.company_id == company_id, Notification.is_read == False)  # noqa: E712
        .count()
    )

    sev = {"심각": 0, "위험": 0, "주의": 0, "관심": 0}
    for a in alerts:
        sev[a.severity] = sev.get(a.severity, 0) + 1
    sev_txt = ", ".join(f"{k} {v}건" for k, v in sev.items() if v) or "없음"

    kpis = compute_kpis(db, company_id)
    rev_txt = ""
    if kpis.get("has_data"):
        rev_txt = (f"최근 월({kpis['month']}) 매출 {fmt_krw(kpis['revenue'])}, "
                   f"영업이익률 {kpis['op_margin']}%. ")

    msg = (
        f"{rev_txt}미해결 위험 알림 {len(alerts)}건(등급별: {sev_txt}), "
        f"최근 7일 신규 분석 {analyses}건, 읽지 않은 알림 {unread}건입니다. "
        "주간 경영 점검 회의에서 우선순위를 확인하세요."
    )
    return _mk_notification(db, company_id, "weekly", "주간 경영 요약", msg)
