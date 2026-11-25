"""통합 경영 대시보드 집계 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import (
    AnalysisResult, CustomerMonthly, FinancialMonthly, MarketSeries, NewsItem,
    Notification, ProductMonthly, Report, RiskAlert, User,
)
from ..services.analysis_engine import compute_kpis
from ..utils import company_or_common, fmt_krw, month_range

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cid = user.company_id
    kpis = compute_kpis(db, cid)
    months = month_range(12)

    # 월별 재무 (12개월)
    fin = (
        db.query(FinancialMonthly)
        .filter(FinancialMonthly.company_id == cid, FinancialMonthly.month.in_(months))
        .order_by(FinancialMonthly.month)
        .all()
    )
    monthly = [
        {"month": f.month, "revenue": f.revenue, "operating_profit": f.operating_profit,
         "raw_material_cost": f.raw_material_cost, "labor_cost": f.labor_cost,
         "other_cost": f.other_cost, "fx_avg_rate": f.fx_avg_rate}
        for f in fin
    ]

    # 비용 구성 (최근월)
    last = fin[-1] if fin else None
    cost_mix = []
    if last and last.revenue:
        cost_mix = [
            {"name": "원자재", "value": last.raw_material_cost, "pct": round(last.raw_material_cost / last.revenue * 100, 1)},
            {"name": "인건비", "value": last.labor_cost, "pct": round(last.labor_cost / last.revenue * 100, 1)},
            {"name": "기타", "value": last.other_cost, "pct": round(last.other_cost / last.revenue * 100, 1)},
        ]

    # 환율 추이 (12개월)
    fx = (
        db.query(MarketSeries)
        .filter(company_or_common(MarketSeries.company_id, cid),
                MarketSeries.series_key == "USD_KRW",
                MarketSeries.month.in_(months))
        .order_by(MarketSeries.month).all()
    )
    fx_series = [{"month": x.month, "value": x.value} for x in fx]

    # 위험 현황
    alerts = db.query(RiskAlert).filter(RiskAlert.company_id == cid).all()
    severity_order = ["심각", "위험", "주의", "관심", "정상"]
    risk_summary = {s: 0 for s in severity_order}
    unread = 0
    for a in alerts:
        risk_summary[a.severity] = risk_summary.get(a.severity, 0) + 1
        if a.status == "unread":
            unread += 1

    # 미처리 후속조치
    from ..models import FollowUp, Decision
    open_fu = db.query(FollowUp).filter(
        FollowUp.company_id == cid, FollowUp.status != "완료").count()
    pending_dec = db.query(Decision).filter(
        Decision.company_id == cid, Decision.status.in_(["검토 대기", "검토 중"])).count()

    # 뉴스/분석/보고서 최근
    news = (
        db.query(NewsItem).filter(company_or_common(NewsItem.company_id, cid))
        .order_by(NewsItem.published_at.desc()).limit(5).all()
    )
    analyses = (
        db.query(AnalysisResult).filter(AnalysisResult.company_id == cid)
        .order_by(AnalysisResult.created_at.desc()).limit(3).all()
    )
    reports = (
        db.query(Report).filter(Report.company_id == cid)
        .order_by(Report.created_at.desc()).limit(3).all()
    )
    notifs = (
        db.query(Notification).filter(Notification.company_id == cid)
        .order_by(Notification.created_at.desc()).limit(5).all()
    )

    return {
        "kpis": {
            **{k: kpis.get(k) for k in [
                "month", "revenue", "operating_profit", "op_margin",
                "revenue_mom", "revenue_yoy", "op_mom", "op_yoy", "op_margin_yoy",
                "raw_material_ratio", "fx_avg_rate", "fx_mom_pct_series", "export_ratio",
            ]},
            "revenue_fmt": fmt_krw(kpis.get("revenue", 0)),
            "operating_profit_fmt": fmt_krw(kpis.get("operating_profit", 0)),
        },
        "has_data": kpis.get("has_data", False),
        "monthly": monthly,
        "cost_mix": cost_mix,
        "product_margin": kpis.get("product_margin", []),
        "customer_concentration": kpis.get("customer_concentration", []),
        "fx_series": fx_series,
        "risk_summary": risk_summary,
        "unread_alerts": unread,
        "open_followups": open_fu,
        "pending_decisions": pending_dec,
        "recent_news": [
            {"id": n.id, "title": n.title, "category": n.category, "sentiment": n.sentiment,
             "importance": n.importance, "relevance_score": n.relevance_score,
             "published_at": n.published_at.isoformat() if n.published_at else ""}
            for n in news
        ],
        "recent_analyses": [
            {"id": a.id, "analysis_type": a.analysis_type, "title": a.title,
             "summary": a.summary[:150], "status": a.status,
             "created_at": a.created_at.isoformat() if a.created_at else ""}
            for a in analyses
        ],
        "recent_reports": [
            {"id": r.id, "period": r.period, "title": r.title,
             "created_at": r.created_at.isoformat() if r.created_at else ""}
            for r in reports
        ],
        "notifications": [
            {"id": n.id, "ntype": n.ntype, "title": n.title, "is_read": n.is_read,
             "created_at": n.created_at.isoformat() if n.created_at else ""}
            for n in notifs
        ],
        "demo_disclaimer": "모든 수치는 데모용 가상 데이터 및 규칙 기반 분석 결과입니다.",
    }
