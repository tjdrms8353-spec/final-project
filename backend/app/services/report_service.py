"""월간 경영 보고서 생성 + PDF 출력."""
import os
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from ..config import DATA_DIR
from ..models import (
    AnalysisResult, AuditLog, Company, Decision, FollowUp, FinancialMonthly,
    MarketSeries, NewsItem, Notification, NotificationSetting, Report, RiskAlert,
)
from ..utils import company_or_common, fmt_krw, month_range, prev_month
from .analysis_engine import compute_kpis

REPORT_DIR = DATA_DIR / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

DISCLAIMER = "본 보고서는 내부 경영 검토용 데모 문서이며 회계 감사 또는 공식 재무제표를 대체하지 않습니다."


def build_report_content(db: Session, company_id: int, period: str) -> dict:
    company = db.get(Company, company_id)
    kpis = compute_kpis(db, company_id)
    month = period if period else (kpis.get("month") or month_range(1)[0])

    fin = (
        db.query(FinancialMonthly)
        .filter(FinancialMonthly.company_id == company_id, FinancialMonthly.month == month)
        .first()
    )
    prev_f = (
        db.query(FinancialMonthly)
        .filter(FinancialMonthly.company_id == company_id, FinancialMonthly.month == prev_month(month))
        .first()
    )

    news = (
        db.query(NewsItem)
        .filter(company_or_common(NewsItem.company_id, company_id))
        .order_by(NewsItem.published_at.desc())
        .limit(8)
        .all()
    )
    analyses = (
        db.query(AnalysisResult)
        .filter(AnalysisResult.company_id == company_id)
        .order_by(AnalysisResult.created_at.desc())
        .limit(6)
        .all()
    )
    alerts = (
        db.query(RiskAlert)
        .filter(RiskAlert.company_id == company_id)
        .order_by(RiskAlert.created_at.desc())
        .limit(10)
        .all()
    )
    decisions = (
        db.query(Decision)
        .filter(Decision.company_id == company_id)
        .order_by(Decision.updated_at.desc())
        .limit(10)
        .all()
    )
    followups = (
        db.query(FollowUp)
        .filter(FollowUp.company_id == company_id)
        .order_by(FollowUp.updated_at.desc())
        .limit(10)
        .all()
    )

    def delta(cur, old):
        if not cur or not old:
            return None
        return round((cur - old) / abs(old) * 100, 1) if old else None

    return {
        "period": month,
        "generated_at": datetime.utcnow().isoformat(),
        "disclaimer": DISCLAIMER,
        "is_demo": True,
        "company": {
            "name": company.name if company else "",
            "industry": company.industry if company else "",
            "size": company.size if company else "",
        },
        "kpi_summary": {
            "revenue": kpis.get("revenue"),
            "operating_profit": kpis.get("operating_profit"),
            "op_margin": kpis.get("op_margin"),
            "revenue_yoy": kpis.get("revenue_yoy"),
            "op_margin_yoy": kpis.get("op_margin_yoy"),
            "fx_latest": kpis.get("fx_latest"),
        },
        "monthly_financial": {
            "month": month,
            "revenue": fin.revenue if fin else None,
            "operating_profit": fin.operating_profit if fin else None,
            "revenue_mom_pct": delta(fin.revenue if fin else None, prev_f.revenue if prev_f else None),
            "op_mom_pct": delta(fin.operating_profit if fin else None, prev_f.operating_profit if prev_f else None),
            "raw_material_cost": fin.raw_material_cost if fin else None,
            "labor_cost": fin.labor_cost if fin else None,
        },
        "market": {
            "fx_mom_pct": kpis.get("fx_mom_pct_series"),
            "negative_news": kpis.get("negative_news_count"),
        },
        "top_news": [
            {"title": n.title, "category": n.category, "sentiment": n.sentiment,
             "importance": n.importance, "source": n.source,
             "published_at": n.published_at.isoformat() if n.published_at else ""}
            for n in news[:5]
        ],
        "analyses": [
            {"type": a.analysis_type, "title": a.title, "summary": a.summary,
             "status": a.status, "engine": a.engine}
            for a in analyses
        ],
        "alerts": [
            {"severity": a.severity, "category": a.category, "title": a.title, "status": a.status}
            for a in alerts
        ],
        "decisions": [
            {"title": (a.title if a else "직접 등록"), "status": d.status,
             "decision": d.decision, "assignee": d.assignee}
            for d in decisions for a in [
                db.get(AnalysisResult, d.analysis_result_id) if d.analysis_result_id else None
            ]
        ][:10],
        "followups": [
            {"title": f.title, "status": f.status, "assignee": f.assignee,
             "due_date": f.due_date}
            for f in followups
        ],
    }


def create_report(db: Session, company_id: int, period: str, user_name: str) -> Report:
    content = build_report_content(db, company_id, period)
    title = f"{content['company']['name']} {period} 월간 경영 보고서 (데모)"
    r = Report(company_id=company_id, period=period, title=title,
               content=content, created_by=user_name)
    db.add(r)
    db.flush()
    # PDF 즉시 생성 시도 (폰트 없으면 경로만 기록)
    try:
        pdf_path = render_pdf(content, r.id)
        r.pdf_path = pdf_path
    except Exception:
        r.pdf_path = ""
    return r


def _font_path() -> str | None:
    candidates = [
        r"C:\Windows\Fonts\malgun.ttf",
        r"C:\Windows\Fonts\gulim.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def render_pdf(content: dict, report_id: int) -> str:
    from fpdf import FPDF

    class PDF(FPDF):
        def footer(self):
            self.set_y(-12)
            self.set_font("korean" if _font_path() else "helvetica", "", 8)
            self.cell(0, 8, f"dayribbon 데모 보고서 #{report_id} - 내부 검토용", align="C")

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _font_path()
    if font:
        pdf.add_font("korean", "", font)
        pdf.add_font("korean", "B", font)
        pdf.set_font("korean", "", 10)
    else:
        pdf.set_font("helvetica", "", 10)

    def w(t):
        pdf.write(5, t)

    w(f"[데모] {content['company']['name']} 월간 경영 보고서")
    pdf.ln(2)
    w(f"기간: {content['period']}  |  생성일시: {content['generated_at'][:16].replace('T',' ')} UTC")
    pdf.ln(4)
    w(content["disclaimer"])
    pdf.ln(8)

    w("■ 경영 요약 KPI")
    pdf.ln(2)
    k = content["kpi_summary"]
    w(f"- 매출: {fmt_krw(k['revenue'] or 0)} | 영업이익: {fmt_krw(k['operating_profit'] or 0)} | 영업이익률: {k['op_margin']}%")
    w(f"- 매출 전년동기: {k['revenue_yoy']}% | 영업이익률 전년동월: {k['op_margin_yoy']}%p | 환율: {k['fx_latest']}")
    pdf.ln(4)

    m = content["monthly_financial"]
    w(f"■ {m['month']} 월별 재무 (전월 대비 매출 {m['revenue_mom_pct']}%, 영업이익 {m['op_mom_pct']}%)")
    pdf.ln(2)
    w(f"- 매출 {fmt_krw(m['revenue'] or 0)} / 영업이익 {fmt_krw(m['operating_profit'] or 0)}")
    w(f"- 원자재비 {fmt_krw(m['raw_material_cost'] or 0)} / 인건비 {fmt_krw(m['labor_cost'] or 0)}")
    pdf.ln(4)

    w("■ 시장 환경")
    pdf.ln(2)
    w(f"- 환율 전월 대비: {content['market']['fx_mom_pct']}% | 부정적 뉴스 {content['market']['negative_news']}건")
    pdf.ln(4)

    w("■ 주요 뉴스")
    pdf.ln(2)
    for n in content["top_news"]:
        w(f"- [{n['category']}/{n['sentiment']}] {n['title']} ({n['source']}, {n['published_at'][:10]})")
    pdf.ln(4)

    w("■ 분석 결과 (규칙 기반 데모 분석)")
    pdf.ln(2)
    for a in content["analyses"]:
        w(f"- [{a['type']}] {a['title']}: {a['summary'][:120]}")
    pdf.ln(4)

    w("■ 위험 알림 현황")
    pdf.ln(2)
    if content["alerts"]:
        for a in content["alerts"]:
            w(f"- [{a['severity']}] {a['title']} ({a['status']})")
    else:
        w("- 없음")
    pdf.ln(4)

    w("■ 관리자 의사결정 및 후속 조치")
    pdf.ln(2)
    for d in content["decisions"][:5]:
        w(f"- {d['title']} → {d['status']} {d['decision']}")
    for f in content["followups"][:5]:
        w(f"- 후속조치: {f['title']} [{f['status']}] 담당 {f['assignee']} 기한 {f['due_date']}")
    if not content["decisions"] and not content["followups"]:
        w("- 없음")

    pdf.ln(8)
    w("※ 본 문서는 등록된 데모 데이터 기반 자동 생성 문서이며, 법적 효력이 없습니다.")

    fname = f"report_{report_id}_{content['period']}.pdf"
    path = REPORT_DIR / fname
    pdf.output(str(path))
    return str(path)


def _report_email_body(content: dict) -> str:
    """월간 보고서 이메일 본문 — KPI·재무·알림 요약을 텍스트로 구성."""
    k = content.get("kpi_summary") or {}
    fin = content.get("monthly_financial") or {}
    lines = [
        f"{content['company']['name']} {content['period']} 월간 경영 보고서입니다.",
        "",
        "[경영 요약]",
    ]
    if k.get("revenue") is not None:
        lines.append(
            f"매출 {fmt_krw(k['revenue'])} / 영업이익 {fmt_krw(k.get('operating_profit') or 0)}"
            f" / 영업이익률 {k.get('op_margin')}%")
    if k.get("revenue_yoy") is not None:
        lines.append(f"매출 전년동월 대비 {k['revenue_yoy']}%")
    if fin.get("revenue_mom_pct") is not None:
        lines.append(f"매출 전월 대비 {fin['revenue_mom_pct']}%")
    if k.get("fx_latest"):
        lines.append(f"기준 환율 {k['fx_latest']}")
    if len(lines) == 3:
        lines.append("재무 데이터가 아직 등록되지 않았습니다.")

    alerts = content.get("alerts") or []
    open_alerts = [a for a in alerts if a.get("status") != "acknowledged"]
    lines += ["", f"[위험 알림] 미해결 {len(open_alerts)}건"]
    lines += [f"- [{a['severity']}] {a['title']}" for a in open_alerts[:5]]

    lines += [
        "",
        "전체 보고서는 첨부 PDF 또는 dayribbon 분기 경영 보고서 메뉴에서 확인할 수 있습니다.",
        "",
        content.get("disclaimer", ""),
    ]
    return "\n".join(lines)


def dispatch_monthly_reports(db: Session) -> list[Report]:
    """이전 달 월간 보고서를 자동 생성하고 이메일 발송 큐에 등록한다.

    스케줄러에서 매 틱 호출 — (기업, 기간)별 자동 보고서가 이미 있으면 건너뛰어
    중복 생성·발송되지 않는다. 알림 설정 email_enabled가 꺼진 기업은
    보고서만 생성하고 발송하지 않는다. PDF 첨부는 폰트가 있어 생성된 경우만.
    """
    from .delivery_service import _email_recipients, enqueue_delivery

    period = (datetime.utcnow().replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    out = []
    for c in db.query(Company).all():
        exists = (db.query(Report)
                  .filter(Report.company_id == c.id, Report.period == period,
                          Report.created_by == "시스템 자동")
                  .first())
        if exists:
            continue
        r = create_report(db, c.id, period, "시스템 자동")
        st = (db.query(NotificationSetting)
              .filter(NotificationSetting.company_id == c.id).first())
        if not st or st.email_enabled:
            for addr in _email_recipients(db, c.id):
                enqueue_delivery(
                    db, c.id, "email", addr,
                    f"{c.name} {period} 월간 경영 보고서",
                    _report_email_body(r.content),
                    attachment_path=r.pdf_path or "")
        out.append(r)
    return out
