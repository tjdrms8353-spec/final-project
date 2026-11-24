"""Weekly/monthly management report generation.

Every number in a report comes from SQL/Polars (metrics.py) or stored rows;
nothing is invented. Sections with no data in the period say so explicitly.
"""

import calendar
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analysis import company_records
from .industries import get_template, template_dict
from .market import change_over, indicator_series
from .metrics import monthly_summary
from .models import AnalysisFinding, AnalysisRun, BiUser, Company, Decision, ErpUpload, FollowUpAction

# Report periods are Korean calendar days; stored timestamps are naive UTC.
KST = timedelta(hours=9)


def today_kst() -> date:
    return (datetime.now(timezone.utc) + KST).date()


def month_bounds(anchor: date) -> tuple[date, date]:
    start = date(anchor.year, anchor.month, 1)
    return start, date(anchor.year, anchor.month, calendar.monthrange(anchor.year, anchor.month)[1])


def week_bounds(anchor: date) -> tuple[date, date]:
    start = anchor - timedelta(days=anchor.weekday())
    return start, start + timedelta(days=6)


def _in_range(ts: datetime, start: date, end: date) -> bool:
    return start <= ts.date() <= end


def _names(db: Session, ids: set[int]) -> dict[int, str]:
    if not ids:
        return {}
    return dict(db.execute(select(BiUser.id, BiUser.name).where(BiUser.id.in_(ids))).all())


def _kpi_section(template, monthly: list[dict], month: str) -> tuple[list[dict], str | None]:
    """KPIs for `month`, or the latest earlier month with data (returned period says which)."""
    candidates = [i for i, r in enumerate(monthly) if r["period"] <= month]
    if not candidates:
        return [], None
    index = candidates[-1]
    current, previous = monthly[index], monthly[index - 1] if index > 0 else None
    return [{**k.__dict__, "value": current.get(k.code), "previous": previous.get(k.code) if previous else None}
            for k in template.kpis], current["period"]


def _weekly_summary(records: list[dict], start: date, end: date) -> dict:
    sales = purchase = expense = 0.0
    inventory = None
    count = 0
    for r in records:
        d = r["record_date"]
        if isinstance(d, str):
            d = date.fromisoformat(d)
        if r["category"] == "inventory":
            if d <= end and (inventory is None or d > inventory[0]):
                inventory = (d, r["amount"])
            continue
        if start <= d <= end:
            count += 1
            if r["category"] == "sales":
                sales += r["amount"]
            elif r["category"] == "purchase":
                purchase += r["amount"]
            elif r["category"] == "expense":
                expense += r["amount"]
    return {"sales": round(sales, 2), "purchase": round(purchase, 2), "expense": round(expense, 2),
            "operating_profit": round(sales - purchase - expense, 2),
            "inventory": inventory[1] if inventory else None, "record_count": count}


def build_report(db: Session, company: Company, kind: str, anchor: date, user: BiUser) -> dict:
    template = get_template(company.industry)
    start, end = month_bounds(anchor) if kind == "monthly" else week_bounds(anchor)
    label = f"{start.year}년 {start.month}월" if kind == "monthly" else \
        f"{start.year}년 {start.month}월 {start.day}일(월) ~ {end.month}월 {end.day}일(일)" if start.month == end.month else \
        f"{start.year}년 {start.month}월 {start.day}일(월) ~ {end.year}년 {end.month}월 {end.day}일(일)"

    records = company_records(db, company.id)
    monthly = monthly_summary(records)
    kpis, kpi_period = _kpi_section(template, monthly, f"{start.year}-{start.month:02d}") if kind == "monthly" \
        else _kpi_section(template, monthly, f"{end.year}-{end.month:02d}")

    start_dt = datetime(start.year, start.month, start.day) - KST
    end_dt = datetime(end.year, end.month, end.day) + timedelta(days=1) - KST

    runs = db.scalars(select(AnalysisRun).where(AnalysisRun.company_id == company.id,
                                                AnalysisRun.created_at >= start_dt,
                                                AnalysisRun.created_at < end_dt)
                      .order_by(AnalysisRun.id)).all()
    run_ids = [r.id for r in runs]
    findings = db.scalars(select(AnalysisFinding).where(AnalysisFinding.run_id.in_(run_ids))).all() if run_ids else []
    by_run: dict[int, list] = {}
    for f in findings:
        by_run.setdefault(f.run_id, []).append({"id": f.id, "kind": f.kind, "severity": f.severity, "title": f.title,
                                                "status": f.status, "recommendation": f.recommendation})
    analysis = [{"id": r.id, "period": r.period, "created_at": r.created_at.isoformat(),
                 "narrative_source": r.narrative_source, "narrative": r.narrative,
                 "findings": by_run.get(r.id, [])} for r in runs]

    decisions = db.execute(select(Decision, AnalysisFinding.title)
                           .join(AnalysisFinding, AnalysisFinding.id == Decision.finding_id)
                           .where(Decision.company_id == company.id,
                                  Decision.decided_at >= start_dt, Decision.decided_at < end_dt)
                           .order_by(Decision.id)).all()
    names = _names(db, {d.decided_by for d, _ in decisions} | {d.assignee_id for d, _ in decisions if d.assignee_id})
    decision_rows = [{"id": d.id, "finding_title": title, "status": d.status, "reason": d.reason,
                      "decided_by": names.get(d.decided_by, "-"), "assignee": names.get(d.assignee_id),
                      "decided_at": d.decided_at.isoformat()} for d, title in decisions]

    actions = db.scalars(select(FollowUpAction).where(FollowUpAction.company_id == company.id,
                                                       FollowUpAction.updated_at >= start_dt,
                                                       FollowUpAction.updated_at < end_dt)
                         .order_by(FollowUpAction.id)).all()
    action_names = _names(db, {a.assignee_id for a in actions if a.assignee_id})
    action_rows = [{"id": a.id, "title": a.title, "status": a.status,
                    "assignee": action_names.get(a.assignee_id),
                    "due_date": a.due_date.isoformat() if a.due_date else None} for a in actions]
    open_actions = db.scalars(select(FollowUpAction).where(FollowUpAction.company_id == company.id,
                                                            FollowUpAction.status != "DONE")).all()

    uploads = db.scalars(select(ErpUpload).where(ErpUpload.company_id == company.id,
                                                  ErpUpload.uploaded_at >= start_dt,
                                                  ErpUpload.uploaded_at < end_dt)
                         .order_by(ErpUpload.id)).all()
    upload_rows = [{"id": u.id, "file_name": u.file_name, "row_count": u.row_count,
                    "rejected_count": u.rejected_count, "uploaded_at": u.uploaded_at.isoformat()} for u in uploads]

    indicators = []
    for code in company.interest_indicators or template.market_indicators:
        series = indicator_series(db, code)
        latest = series[-1] if series else None
        change = change_over(series)
        if latest or change:
            indicators.append({"code": code, "latest_date": latest.obs_date.isoformat() if latest else None,
                               "latest_value": latest.value if latest else None,
                               "change_30d_pct": change["change_pct"] if change else None,
                               "source": latest.source if latest else "Frankfurter (ECB 기준환율)"})

    return {
        "kind": kind, "period": label, "start": start.isoformat(), "end": end.isoformat(),
        "generated_at": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds"), "generated_by": user.name,
        "company": {"name": company.name, "industry": company.industry, "industry_label": template.label},
        "template": template_dict(template),
        "summary": {"weekly": _weekly_summary(records, start, end)} if kind == "weekly" else {},
        "kpis": kpis, "kpi_period": kpi_period,
        "monthly_rows": [r for r in monthly if r["period"] <= (kpi_period or "")][-6:],
        "analysis": analysis, "decisions": decision_rows, "actions": action_rows,
        "open_actions_count": len(open_actions),
        "uploads": upload_rows, "indicators": indicators,
    }
