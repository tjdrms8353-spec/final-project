"""외부 데이터 수집 오케스트레이션 (정식 전환 B).

- 등록된 수집기(ALL_COLLECTORS)를 실행해 결과를 기업별로 저장한다.
- MarketSeries: (company_id, series_key, month) 유니크로 upsert — 재수집 시 중복 없이 최신값 갱신.
- NewsItem: (company_id, link 또는 title) 기준 중복 차단 — 실수집분은 is_demo=False·출처 표기.
- 수집 결과는 감사 로그에 기록하고, 모듈 상태에 마지막 실행 정보를 보관한다(모니터링용).
"""
import re
from datetime import datetime

from sqlalchemy.orm import Session

from ..models import AuditLog, Company, MarketSeries, NewsItem
from .collectors import ALL_COLLECTORS

# 마지막 수집 실행 정보 (프로세스 내 상태 — 모니터링 API가 읽는다)
LAST_RUN: dict = {"at": None, "summary": []}

# 뉴스 분류 키워드 (단순 규칙 — LLM 분류는 전환 C에서 고도화 가능)
_CATEGORY_RULES = [
    ("환율", ("환율", "달러", "엔화", "위안", "유로", "원화")),
    ("금리", ("금리", "기준금리", "한국은행", "연준", "금통위")),
    ("공급망", ("공급망", "물류", "운임", "항만", "해운", "수급")),
    ("원자재", ("원자재", "구리", "철강", "유가", "알루미늄", "니켈", "리튬", "반도체")),
    ("수출입", ("수출", "수입", "무역", "관세", "통상", "무역수지")),
]
_NEG_WORDS = ("급등", "급락", "하락", "위기", "리스크", "중단", "적자", "폭락",
              "상승세 꺾", "경고", "불안", "침체", "충격", "제재")
_POS_WORDS = ("상승", "성장", "수주", "확대", "호조", "개선", "회복", "증가", "최대")


def classify_news(title: str, summary: str) -> tuple[str, str]:
    """제목+요약 키워드로 (카테고리, 감성)을 추정한다."""
    text = f"{title} {summary}"
    category = next((cat for cat, words in _CATEGORY_RULES
                     if any(w in text for w in words)), "거시경제")
    neg = sum(1 for w in _NEG_WORDS if w in text)
    pos = sum(1 for w in _POS_WORDS if w in text)
    sentiment = "negative" if neg > pos else "positive" if pos > neg else "neutral"
    return category, sentiment


def company_keywords(company: Company) -> list[str]:
    """기업 프로필에서 뉴스 관련도 스코어링용 키워드를 뽑는다."""
    fields = [company.industry, company.products, company.raw_materials,
              company.interest_areas, company.risk_concerns,
              company.export_countries, company.import_countries]
    words: list[str] = []
    for f in fields:
        for w in re.split(r"[,/\s]+", f or ""):
            w = w.strip()
            if len(w) >= 2:
                words.append(w)
    return words


def score_relevance(title: str, summary: str, keywords: list[str]) -> tuple[int, str]:
    """(관련도 0~100, 매칭 키워드 설명)을 반환한다."""
    text = f"{title} {summary}"
    hits = [w for w in keywords if w in text]
    score = min(100, 40 + len(set(hits)) * 15)
    return score, ", ".join(sorted(set(hits)))


def _upsert_series(db: Session, company_id: int, rows: list[dict]) -> int:
    """시계열을 (company, key, month) 기준 upsert한다. 처리 건수를 반환."""
    n = 0
    for r in rows:
        rec = (db.query(MarketSeries)
               .filter_by(company_id=company_id, series_key=r["series_key"],
                          month=r["month"]).first())
        if rec:
            rec.value = r["value"]
            rec.source = r.get("source") or rec.source
            rec.series_name = r.get("series_name") or rec.series_name
            rec.unit = r.get("unit") or rec.unit
        else:
            db.add(MarketSeries(company_id=company_id, **r))
        n += 1
    return n


def _insert_news(db: Session, company: Company, rows: list[dict]) -> int:
    """수집 뉴스를 중복 없이 저장한다. 처리 건수를 반환."""
    existing = {
        (n.link or n.title) for n in
        db.query(NewsItem.link, NewsItem.title)
        .filter(NewsItem.company_id == company.id).all()
    }
    keywords = company_keywords(company)
    n = 0
    for r in rows:
        dedup_key = r.get("link") or r["title"]
        if dedup_key in existing:
            continue
        existing.add(dedup_key)
        cat, sent = classify_news(r["title"], r.get("summary", ""))
        score, hits = score_relevance(r["title"], r.get("summary", ""), keywords)
        db.add(NewsItem(
            company_id=company.id, title=r["title"],
            summary=r.get("summary", ""), source=r.get("source", ""),
            link=r.get("link", ""), category=cat, sentiment=sent,
            relevance_score=float(score),
            importance="높음" if score >= 70 else "보통",
            impact_on_company=(f"기업 프로필 키워드({hits})와 연관 — 영향도 확인 필요"
                               if hits else ""),
            why_relevant=(f"기업 관심 키워드 매칭: {hits}" if hits
                          else "일반 거시경제 뉴스"),
            published_at=r.get("published_at") or datetime.utcnow(),
            is_demo=False,
        ))
        n += 1
    return n


def collectors_status() -> list[dict]:
    """수집기별 이름/출처/활성 여부."""
    return [{"name": c.name, "source": c.source, "enabled": c.enabled}
            for c in (cls() for cls in ALL_COLLECTORS)]


def run_collection(db: Session, company_id: int | None = None) -> dict:
    """수집기를 실행해 결과를 기업별로 저장한다.

    company_id=None이면 모든 기업에 적용(스케줄러). 반환: 수집 요약 dict.
    """
    companies = ([db.get(Company, company_id)] if company_id
                 else db.query(Company).all())
    companies = [c for c in companies if c]
    summary: list[dict] = []
    series_total = news_total = 0

    for cls in ALL_COLLECTORS:
        collector = cls()
        entry = {"name": collector.name, "source": collector.source,
                 "enabled": collector.enabled, "series": 0, "news": 0, "errors": []}
        if collector.enabled:
            try:
                result = collector.collect()
            except Exception as e:  # 수집기 내부 예외도 서비스 중단 없이 기록
                result = None
                entry["errors"].append(f"{collector.name} 수집 예외: {e}")
            if result is not None:
                entry["errors"].extend(result.errors)
                for r in result.series:
                    r.setdefault("source", result.source)
                for company in companies:
                    entry["series"] += _upsert_series(db, company.id, result.series)
                    entry["news"] += _insert_news(db, company, result.news)
        else:
            entry["errors"].append("비활성 — API 키/설정 없음")
        series_total += entry["series"]
        news_total += entry["news"]
        summary.append(entry)

    db.add(AuditLog(
        company_id=company_id or 0, user_id=None, user_name="(시스템)",
        user_role="", action="collection.run", target_type="collectors",
        target_id="", detail=f"시계열 {series_total}건, 뉴스 {news_total}건 처리"))
    db.commit()

    LAST_RUN["at"] = datetime.utcnow().isoformat()
    LAST_RUN["summary"] = summary
    return {"ran_at": LAST_RUN["at"], "companies": len(companies),
            "collectors": summary}
