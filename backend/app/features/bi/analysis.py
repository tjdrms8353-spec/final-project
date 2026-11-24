"""Evidence-based opportunity/risk analysis.

Numbers come from SQL/Polars (metrics.py, market.py). Rules decide findings. The optional
LLM only rephrases verified facts; its output is rejected if it introduces new numbers.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.features.trends.models import NewsArticle, NewsTranslation

from .industries import get_template
from .market import change_over, indicator_series
from .metrics import monthly_summary, sales_trend
from .models import AnalysisFinding, AnalysisRun, Company, ErpRecord, ErpUpload

log = logging.getLogger(__name__)


def _fmt(value: float | None, unit: str = "") -> str:
    if value is None:
        return "-"
    if unit == "KRW":
        return f"{value:,.0f}원"
    return f"{value:,.2f}{unit}"


def company_records(db: Session, company_id: int) -> list[dict]:
    rows = db.execute(select(ErpRecord.record_date, ErpRecord.category, ErpRecord.amount, ErpRecord.country)
                      .where(ErpRecord.company_id == company_id)).all()
    return [dict(r._mapping) for r in rows]


def related_news(db: Session, keywords: list[str], days: int = 14, limit: int = 5) -> dict:
    """Search stored news (existing trends module) by company/industry keywords."""
    keywords = [k for k in dict.fromkeys(k.strip() for k in keywords) if k][:12]
    if not keywords:
        return {"available": True, "keywords": [], "recent_count": 0, "previous_count": 0, "items": []}
    conditions = []
    for k in keywords:
        conditions += [NewsArticle.title.contains(k, autoescape=True), NewsArticle.summary.contains(k, autoescape=True),
                       NewsTranslation.title.contains(k, autoescape=True)]
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    base = select(NewsArticle).outerjoin(NewsTranslation, (NewsTranslation.url_hash == NewsArticle.url_hash)
                                         & (NewsTranslation.lang == "ko")).where(or_(*conditions))
    try:
        def count(start, end):
            sub = base.where(NewsArticle.sort_at >= start, NewsArticle.sort_at < end).subquery()
            return db.scalar(select(func.count()).select_from(sub)) or 0
        recent = count(now - timedelta(days=days), now + timedelta(days=1))
        previous = count(now - timedelta(days=days * 2), now - timedelta(days=days))
        items = db.scalars(base.order_by(NewsArticle.sort_at.desc()).limit(limit)).unique().all()
    except SQLAlchemyError:
        db.rollback()
        return {"available": False, "keywords": keywords, "recent_count": 0, "previous_count": 0, "items": []}
    return {
        "available": True, "keywords": keywords, "recent_count": recent, "previous_count": previous, "days": days,
        "items": [{"type": "news", "title": n.title, "url": n.url, "source": n.source,
                   "date": (n.published_at or n.sort_at).isoformat()} for n in items],
    }


def _fact(label, value, unit, source, period):
    return {"label": label, "value": value, "unit": unit, "display": _fmt(value, unit if unit != "%" else "%"),
            "source": source, "period": period}


def build_findings(company: Company, rows: list[dict], fx: dict, news: dict, source_label: str) -> list[dict]:
    template = get_template(company.industry)
    t = template.thresholds
    findings: list[dict] = []
    news_evidence = news["items"][:3]
    news_note = ("관련 뉴스가 수집 DB에 없어 외부 이슈와의 연결은 확인하지 못했습니다."
                 if not news["items"] else f"관련 뉴스 {news['recent_count']}건(최근 {news.get('days', 14)}일)을 참고했습니다.")
    if not rows:
        return findings
    latest = rows[-1]
    prev = rows[-2] if len(rows) > 1 else None
    period = latest["period"]
    erp = {"type": "erp", "title": f"ERP 업로드 데이터 ({source_label})", "source": "기업 업로드", "date": period}

    mom = latest.get("sales_mom_pct")
    if mom is not None and (mom <= t["sales_drop_pct"] or mom >= t["sales_growth_pct"]):
        up = mom > 0
        findings.append({
            "kind": "opportunity" if up else "risk", "severity": "medium" if abs(mom) < 15 else "high",
            "title": f"월 매출 전월 대비 {mom:+.2f}% {'증가' if up else '감소'}",
            "facts": [_fact("당월 매출", latest["sales"], "KRW", "ERP", period),
                      _fact("전월 매출", prev["sales"], "KRW", "ERP", prev["period"]),
                      _fact("전월 대비", mom, "%", "SQL/Polars 계산", period)],
            "inference": ("수요 회복 또는 신규 거래 확대 가능성이 있습니다." if up else
                          "수요 둔화, 거래처 이탈 또는 단가 하락 가능성이 있습니다.") + " (규칙 기반 추론, 원인은 확인되지 않음)",
            "evidence": [erp] + news_evidence,
            "uncertainty": "단월 변동은 계절성·일회성 거래의 영향을 받을 수 있습니다. " + news_note,
            "review_points": ["주요 거래처별 매출 변동 확인", "단가와 판매량 중 어떤 요인인지 분리"],
            "recommendation": "상위 거래처 수주 확대 및 생산 계획 상향 검토" if up else "거래처별 매출 감소 원인 점검 및 재고·생산 조정 검토",
        })

    if prev and latest.get("gross_margin_pct") is not None and prev.get("gross_margin_pct") is not None:
        diff = round(latest["gross_margin_pct"] - prev["gross_margin_pct"], 2)
        if diff <= t["margin_drop_pp"]:
            findings.append({
                "kind": "risk", "severity": "high" if diff <= t["margin_drop_pp"] * 2 else "medium",
                "title": f"매출총이익률 {diff:+.2f}%p 하락",
                "facts": [_fact("당월 매출총이익률", latest["gross_margin_pct"], "%", "SQL/Polars 계산", period),
                          _fact("전월 매출총이익률", prev["gross_margin_pct"], "%", "SQL/Polars 계산", prev["period"]),
                          _fact("당월 매입", latest["purchase"], "KRW", "ERP", period)],
                "inference": "원재료 단가 상승 또는 판매가 하락으로 수익성이 악화되었을 가능성이 있습니다. (규칙 기반 추론)",
                "evidence": [erp] + news_evidence,
                "uncertainty": "매입 시점과 매출 인식 시점 차이로 일시적으로 낮게 계산될 수 있습니다.",
                "review_points": ["주요 원재료 단가 추이 확인", "판매 단가 조정 여부 확인"],
                "recommendation": "원재료 공급처 다변화 및 판매가 반영 여부 검토",
            })

    inv_days = latest.get("inventory_days")
    if inv_days is not None and inv_days >= t["inventory_days_high"]:
        findings.append({
            "kind": "risk", "severity": "medium",
            "title": f"재고 보유일수 {inv_days:.1f}일로 기준({t['inventory_days_high']:.0f}일) 초과",
            "facts": [_fact("월말 재고금액", latest["inventory"], "KRW", "ERP", period),
                      _fact("월 매입", latest["purchase"], "KRW", "ERP", period),
                      _fact("재고 보유일수", inv_days, "일", "SQL/Polars 계산", period)],
            "inference": "재고 누적으로 현금흐름 부담과 재고 평가손실 위험이 커질 수 있습니다. (규칙 기반 추론)",
            "evidence": [erp] + news_evidence,
            "uncertainty": "업종 기준값은 일반적인 참고치이며 기업별 적정 재고 수준은 다를 수 있습니다.",
            "review_points": ["장기 재고 품목 확인", "다음 분기 수주 대비 재고 수준 검토"],
            "recommendation": "생산량 조정 및 재고 소진 계획 수립",
        })

    usd = fx.get("USD/KRW")
    if usd and abs(usd["change_pct"]) >= t["fx_move_pct"]:
        rising = usd["change_pct"] > 0
        fx_share = latest.get("fx_purchase_share_pct") or 0
        export_share = latest.get("export_share_pct") or 0
        fx_ev = {"type": "market", "title": f"USD/KRW {usd['from_value']:.2f} → {usd['to_value']:.2f}",
                 "source": usd["source"], "url": usd["source_url"], "date": usd["to_date"]}
        facts = [_fact("USD/KRW 변동률", usd["change_pct"], "%", usd["source"], f"{usd['from_date']}~{usd['to_date']}"),
                 _fact("외화 매입 비중", fx_share, "%", "SQL/Polars 계산", period),
                 _fact("수출 매출 비중", export_share, "%", "SQL/Polars 계산", period)]
        if fx_share >= t["fx_purchase_share_high"] and rising:
            findings.append({
                "kind": "risk", "severity": "high" if usd["change_pct"] >= t["fx_move_pct"] * 2 else "medium",
                "title": f"원/달러 환율 {usd['change_pct']:+.2f}% 상승 — 외화 매입 원가 부담",
                "facts": facts,
                "inference": "외화 결제 원재료의 원화 환산 원가가 상승할 가능성이 있습니다. (규칙 기반 추론)",
                "evidence": [fx_ev, erp] + news_evidence,
                "uncertainty": "환헤지 계약, 결제 통화(엔·위안 등) 구성은 데이터에 포함되지 않았습니다.",
                "review_points": ["외화 결제 통화별 비중 확인", "환헤지 계약 여부 확인"],
                "recommendation": "선물환 등 환헤지 비율 확대 검토",
            })
        if export_share > 0 and rising:
            findings.append({
                "kind": "opportunity", "severity": "medium",
                "title": f"원/달러 환율 {usd['change_pct']:+.2f}% 상승 — 수출 매출 원화 환산액 증가 여지",
                "facts": facts,
                "inference": "달러 결제 수출 매출의 원화 환산 금액이 늘어날 수 있습니다. (규칙 기반 추론)",
                "evidence": [fx_ev, erp] + news_evidence,
                "uncertainty": "수출 대금의 결제 통화와 시점이 데이터에 포함되지 않았습니다.",
                "review_points": ["수출 계약 통화 확인", "가격 경쟁력 활용 여부 검토"],
                "recommendation": "달러 결제 수출 물량 확대 및 가격 정책 검토",
            })
        if not rising and fx_share >= t["fx_purchase_share_high"]:
            findings.append({
                "kind": "opportunity", "severity": "low",
                "title": f"원/달러 환율 {usd['change_pct']:+.2f}% 하락 — 외화 매입 원가 절감 여지",
                "facts": facts,
                "inference": "외화 결제 원재료의 원화 환산 원가가 낮아질 수 있습니다. (규칙 기반 추론)",
                "evidence": [fx_ev, erp] + news_evidence,
                "uncertainty": "환율 하락이 지속될지는 알 수 없습니다.",
                "review_points": ["원재료 선구매 여력 확인"],
                "recommendation": "원재료 선구매 또는 장기 계약 검토",
            })

    annual_import = getattr(company, "annual_import_krw", None)
    scenario_pct = t.get("fx_scenario_pct", t["fx_move_pct"])
    if annual_import and usd and abs(usd["change_pct"]) >= scenario_pct:
        rising = usd["change_pct"] > 0
        impact = round(annual_import * usd["change_pct"] / 100)
        fx_ev = {"type": "market", "title": f"USD/KRW {usd['from_value']:.2f} → {usd['to_value']:.2f}",
                 "source": usd["source"], "url": usd["source_url"], "date": usd["to_date"]}
        profile_ev = {"type": "company", "title": "기업 정보 — 연간 수입 규모", "source": "기업 등록 정보"}
        findings.append({
            "kind": "risk" if rising else "opportunity",
            "severity": "high" if abs(usd["change_pct"]) >= t["fx_move_pct"] * 2 else "medium",
            "title": (f"환율 {usd['change_pct']:+.1f}% {'상승' if rising else '하락'} 시 "
                      f"연간 수입 비용 약 {_fmt(abs(impact), 'KRW')} {'증가' if rising else '감소'} 시나리오"),
            "facts": [
                _fact("USD/KRW 변동률", usd["change_pct"], "%", usd["source"], f"{usd['from_date']}~{usd['to_date']}"),
                _fact("연간 수입 규모(기업 입력)", annual_import, "KRW", "기업 등록 정보", "연간"),
                _fact("환율 변동 단순 적용 시 영향", impact, "KRW", "연간 수입 × 환율 변동률 계산", "시나리오"),
            ],
            "inference": ("입력하신 연간 수입 규모에 최근 환율 변동률을 그대로 적용한 단순 시나리오입니다. "
                          + ("외화 결제 비중이 높을수록 실제 원가 부담은 더 커질 수 있습니다." if rising else
                             "수입 원가 부담이 줄어들 여지가 있습니다.")),
            "evidence": [fx_ev, profile_ev, erp],
            "uncertainty": "환헤지 계약, 결제 시점, 수입 통화(엔·위안 등) 구성은 반영되지 않은 단순 계산입니다.",
            "review_points": ["외화 결제 예정 금액 확인", "환헤지 비율 점검", "수입 계약 통화 구성 확인"],
            "recommendation": ("선물환 등 환헤지 비율 확대 및 원자재 가격 재협상 검토" if rising
                               else "수입 물량 확대 또는 선구매 검토"),
        })

    trend = sales_trend(rows)
    if trend and trend["r2"] >= 0.5 and abs(trend["slope_per_month"]) > 0:
        up = trend["slope_per_month"] > 0
        findings.append({
            "kind": "change", "severity": "low",
            "title": f"최근 {trend['months']}개월 매출 {'상승' if up else '하락'} 추세",
            "facts": [_fact("월평균 매출 변화(선형)", trend["slope_per_month"], "KRW", "scikit-learn 선형회귀", period),
                      _fact("다음 달 단순 추정 매출", trend["next_month_projection"], "KRW", "scikit-learn 선형회귀", "추정"),
                      _fact("설명력(R²)", trend["r2"], "", "scikit-learn 선형회귀", period)],
            "inference": "추세가 유지된다는 가정 하의 단순 추정치이며 예측을 보장하지 않습니다.",
            "evidence": [erp],
            "uncertainty": f"표본이 {trend['months']}개월로 적어 신뢰도가 제한적입니다.",
            "review_points": ["추정치를 사업 계획과 비교"],
            "recommendation": "추세를 반영한 다음 달 생산·구매 계획 점검",
        })

    if news["available"] and news["recent_count"] and news["recent_count"] >= max(3, news["previous_count"] * 1.5):
        findings.append({
            "kind": "change", "severity": "low",
            "title": f"관련 산업 뉴스 증가 ({news['previous_count']}건 → {news['recent_count']}건)",
            "facts": [_fact(f"최근 {news['days']}일 관련 기사", news["recent_count"], "건", "뉴스 수집 DB", "최근"),
                      _fact(f"직전 {news['days']}일 관련 기사", news["previous_count"], "건", "뉴스 수집 DB", "직전")],
            "inference": "산업 이슈에 대한 관심이 증가하고 있습니다. 기사 내용에 따라 기회 또는 위험일 수 있습니다.",
            "evidence": news["items"],
            "uncertainty": f"키워드({', '.join(news['keywords'][:5])}) 일치 기준이며 기사 논조는 분석하지 않았습니다.",
            "review_points": ["주요 기사 원문 확인"],
            "recommendation": "관련 기사 검토 후 영향도 판단",
        })
    return findings


_NUMBER = re.compile(r"\d[\d,]*(?:\.\d+)?")


def _numbers(text: str) -> set[str]:
    return {n.replace(",", "").rstrip("0").rstrip(".") for n in _NUMBER.findall(text)}


def template_narrative(company: Company, findings: list[dict], period: str) -> str:
    if not findings:
        return f"{company.name}의 {period} 데이터에서 기준을 넘는 기회·위험 신호가 발견되지 않았습니다."
    parts = [f"{company.name}의 {period} 분석 결과 기회 {sum(f['kind'] == 'opportunity' for f in findings)}건, "
             f"위험 {sum(f['kind'] == 'risk' for f in findings)}건, 변화 {sum(f['kind'] == 'change' for f in findings)}건이 확인되었습니다."]
    parts += [f"- {f['title']}" for f in findings]
    return "\n".join(parts)


def llm_narrative(company: Company, findings: list[dict], period: str) -> str | None:
    settings = get_settings()
    key = settings.llm_api_key.get_secret_value()
    if not key or not findings:
        return None
    facts = [{"title": f["title"], "kind": f["kind"], "facts": [{"label": x["label"], "display": x["display"]} for x in f["facts"]]}
             for f in findings]
    prompt = ("다음은 SQL/Python으로 검증된 중소기업 경영 지표입니다. 제공된 수치만 사용해 관리자용 한국어 요약을 5문장 이내로 작성하세요. "
              "새로운 수치·출처를 만들지 말고, 추론은 '추정'이라고 표시하세요.\n" + json.dumps(
                  {"company": company.name, "period": period, "findings": facts}, ensure_ascii=False))
    try:
        response = httpx.post(f"{settings.llm_base_url.rstrip('/')}/chat/completions", timeout=30,
                              headers={"Authorization": f"Bearer {key}"},
                              json={"model": settings.llm_model, "temperature": 0.2,
                                    "messages": [{"role": "user", "content": prompt}]})
        response.raise_for_status()
        text = response.json()["choices"][0]["message"]["content"].strip()
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        log.warning("LLM narrative failed: %s", type(exc).__name__)
        return None
    allowed = _numbers(json.dumps(facts, ensure_ascii=False) + period + company.name)
    if not _numbers(text) <= allowed:
        log.warning("LLM narrative rejected: introduced numbers not in verified facts")
        return None
    return text


def run_analysis(db: Session, company: Company, user_id: int) -> AnalysisRun:
    rows = monthly_summary(company_records(db, company.id))
    template = get_template(company.industry)
    fx = {}
    for code in template.market_indicators:
        change = change_over(indicator_series(db, code))
        if change:
            fx[code] = change
    news = related_news(db, list(company.main_products) + list(template.news_keywords) + list(company.interest_industries))
    upload = db.scalar(select(ErpUpload).where(ErpUpload.company_id == company.id).order_by(ErpUpload.id.desc()))
    findings = build_findings(company, rows, fx, news, upload.file_name if upload else "없음")
    period = rows[-1]["period"] if rows else "-"
    narrative = llm_narrative(company, findings, period)
    source = "llm" if narrative else "template"
    run = AnalysisRun(
        company_id=company.id, period=period,
        metrics={"monthly": rows, "market": fx, "news": {k: v for k, v in news.items() if k != "items"}},
        narrative=narrative or template_narrative(company, findings, period), narrative_source=source,
        created_by=user_id, created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    db.add(run)
    db.flush()
    for f in findings:
        db.add(AnalysisFinding(run_id=run.id, company_id=company.id, status="PENDING", **f))
    db.flush()
    return run
