"""외부 데이터 수집 오케스트레이션 (정식 전환 B 보완).

저장 구조 원칙:
- 공통 외부 데이터(뉴스 원본·환율·금리 등)는 company_id=NULL로 **한 번만** 저장한다.
- 기업별 관련성은 CompanyNewsScore로 분리 — 기업 수만큼 뉴스를 복제하지 않는다.
- 수집기별 스케줄·이력은 CollectorState/CollectionRun 테이블로 관리한다.
- 수집 실패 시 마지막 정상 데이터가 유지되며 상태에 오류만 기록한다.
"""
import re
import time
from datetime import datetime

from sqlalchemy.orm import Session

from ..config import COLLECT_INTERVAL_SEC
from ..models import (
    AuditLog, CollectionRun, CollectorState, Company, CompanyNewsScore,
    MarketSeries, NewsItem,
)
from .collectors import ALL_COLLECTORS, collector_active

# 수동 수집 실행 제한 (기업 관리자의 무제한 실행 방지) — 기업당 1시간 1회
_MANUAL_RUN_AT: dict[int, float] = {}
MANUAL_RUN_COOLDOWN_SEC = 3600

# 수집기별 기본 주기(초) — 공급처 발표 주기 기준
DEFAULT_SCHEDULES = {
    "exim_fx": 6 * 3600,       # 영업일 일 1회 갱신, 여유 두고 6h
    "ecos_rate": 24 * 3600,    # 월 단위 통계, 하루 1회 확인
    "news_rss": 6 * 3600,
    "gdelt": 6 * 3600,
    "fred": 24 * 3600,         # 일/월 단위 통계
    "eia": 24 * 3600,          # 주/월 단위 통계
    "dart": 12 * 3600,         # 공시 수시 등록
}

# 뉴스 분류 키워드 (단순 규칙 — LLM 분류는 전환 C에서 고도화 가능)
_CATEGORY_RULES = [
    ("환율", ("환율", "달러", "엔화", "위안", "유로", "원화")),
    ("금리", ("금리", "기준금리", "한국은행", "연준", "금통위")),
    ("공급망", ("공급망", "물류", "운임", "항만", "해운", "수급")),
    ("원자재", ("원자재", "구리", "철강", "유가", "알루미늄", "니켈", "리튬", "반도체")),
    ("수출입", ("수출", "수입", "무역", "관세", "통상", "무역수지")),
    ("정책", ("정책", "규제", "지원", "법안", "보조금", "산업부")),
]
_NEG_WORDS = ("급등", "급락", "하락", "위기", "리스크", "중단", "적자", "폭락",
              "경고", "불안", "침체", "충격", "제재", "감소")
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


# ---------- 공통 데이터 저장 ----------

def _upsert_series(db: Session, rows: list[dict]) -> int:
    """시계열을 공통(company_id=NULL) 행으로 upsert한다.

    company_id=NULL은 유니크 제약의 보호를 받지 않으므로(다수 DB에서 NULL은
    서로 다른 값으로 취급) 서비스 레벨에서 조회 후 갱신 방식으로 중복을 차단한다.
    """
    n = 0
    for r in rows:
        rec = (db.query(MarketSeries)
               .filter(MarketSeries.company_id.is_(None),
                       MarketSeries.series_key == r["series_key"],
                       MarketSeries.month == r["month"]).first())
        if rec:
            rec.value = r["value"]
            rec.source = r.get("source") or rec.source
            rec.series_name = r.get("series_name") or rec.series_name
            rec.unit = r.get("unit") or rec.unit
        else:
            db.add(MarketSeries(company_id=None, **r))
        n += 1
    return n


def _insert_common_news(db: Session, rows: list[dict]) -> list[NewsItem]:
    """수집 뉴스를 공통(company_id=NULL)으로 중복 없이 저장한다."""
    existing = {
        (n.link or n.title) for n in
        db.query(NewsItem.link, NewsItem.title)
        .filter(NewsItem.company_id.is_(None)).all()
    }
    created: list[NewsItem] = []
    for r in rows:
        dedup_key = r.get("link") or r["title"]
        if dedup_key in existing:
            continue
        existing.add(dedup_key)
        cat, sent = classify_news(r["title"], r.get("summary", ""))
        item = NewsItem(
            company_id=None, title=r["title"],
            summary=r.get("summary", ""), source=r.get("source", ""),
            link=r.get("link", ""), category=cat, sentiment=sent,
            published_at=r.get("published_at") or datetime.utcnow(),
            is_demo=False,
        )
        db.add(item)
        created.append(item)
    db.flush()  # id 확보 — 이후 기업별 점수 연결에 사용
    return created


def score_news_for_company(db: Session, company: Company,
                           news_items: list[NewsItem] | None = None) -> int:
    """공통 뉴스와 기업을 연결하는 관련성 점수를 생성·갱신한다."""
    if news_items is None:
        news_items = (db.query(NewsItem)
                      .filter(NewsItem.company_id.is_(None)).all())
    if not news_items:
        return 0
    keywords = company_keywords(company)
    existing = {
        s.news_item_id for s in
        db.query(CompanyNewsScore.news_item_id)
        .filter(CompanyNewsScore.company_id == company.id).all()
    }
    n = 0
    for item in news_items:
        if item.id in existing:
            continue
        score, hits = score_relevance(item.title, item.summary or "", keywords)
        db.add(CompanyNewsScore(
            company_id=company.id, news_item_id=item.id,
            relevance_score=float(score),
            importance="높음" if score >= 70 else "보통",
            impact_on_company=(f"기업 프로필 키워드({hits})와 연관 — 영향도 확인 필요"
                               if hits else ""),
            why_relevant=(f"기업 관심 키워드 매칭: {hits}" if hits
                          else "일반 거시경제 뉴스"),
        ))
        n += 1
    return n


def _has_important_scores(db: Session, companies: list,
                          new_items: list[NewsItem]) -> bool:
    """신규 뉴스 중 기업 관련도가 '높음'인 점수가 하나라도 생성됐는지."""
    if not new_items or not companies:
        return False
    ids = [i.id for i in new_items]
    return db.query(CompanyNewsScore).filter(
        CompanyNewsScore.news_item_id.in_(ids),
        CompanyNewsScore.relevance_score >= 70,
        CompanyNewsScore.company_id.in_([c.id for c in companies]),
    ).first() is not None


# ---------- 수집기 상태·스케줄 ----------

def ensure_collector_states(db: Session) -> None:
    """등록 수집기의 상태 행을 생성한다 (첫 실행 시 스케줄 시딩)."""
    for cls in ALL_COLLECTORS:
        c = cls()
        if not db.get(CollectorState, c.name):
            db.add(CollectorState(
                name=c.name, enabled=True,
                interval_sec=DEFAULT_SCHEDULES.get(c.name, COLLECT_INTERVAL_SEC),
            ))
    db.commit()


def due_collectors(db: Session) -> list:
    """지금 수집이 필요한 수집기 인스턴스 목록."""
    ensure_collector_states(db)
    states = {s.name: s for s in db.query(CollectorState).all()}
    now = datetime.utcnow()
    due = []
    for cls in ALL_COLLECTORS:
        c = cls()
        st = states.get(c.name)
        if not st or not st.enabled or not collector_active(c):
            continue
        if st.next_run_at is None or st.next_run_at <= now:
            due.append(c)
    return due


def collectors_status(db: Session | None = None) -> list[dict]:
    """수집기별 이름/출처/활성/스케줄·최신성 상태."""
    states: dict[str, CollectorState] = {}
    if db is not None:
        ensure_collector_states(db)
        states = {s.name: s for s in db.query(CollectorState).all()}
    now = datetime.utcnow()
    out = []
    for cls in ALL_COLLECTORS:
        c = cls()
        st = states.get(c.name)
        stale = bool(st and st.last_success_at and
                     (now - st.last_success_at).total_seconds() > st.interval_sec * 2)
        out.append({
            "name": c.name, "source": c.source,
            "enabled": collector_active(c),       # 키+이용조건 포함 실제 실행 가능 여부
            "configured": c.enabled,              # 키/설정만 기준
            "license_verified": getattr(c, "license_verified", True),
            "schedule_enabled": st.enabled if st else True,
            "interval_sec": st.interval_sec if st else None,
            "last_success_at": st.last_success_at.isoformat() if st and st.last_success_at else None,
            "next_run_at": st.next_run_at.isoformat() if st and st.next_run_at else None,
            "last_error": st.last_error if st else "",
            "stale": stale,   # 마지막 성공이 주기 2배 초과 — 최신성 주의
        })
    return out


def run_collector(db: Session, collector, trigger: str = "schedule",
                  company_id: int | None = None) -> dict:
    """단일 수집기 실행 → 공통 저장 + 기업별 관련성 연결 + 이력·상태 기록."""
    run = CollectionRun(collector=collector.name, trigger=trigger,
                        started_at=datetime.utcnow())
    db.add(run)
    state = db.get(CollectorState, collector.name)
    companies = ([db.get(Company, company_id)] if company_id
                 else db.query(Company).all())
    companies = [c for c in companies if c]

    series_n = news_n = 0
    errors: list[str] = []
    try:
        result = collector.collect()
        errors.extend(result.errors)
        for r in result.series:
            r.setdefault("source", result.source)
        series_n = _upsert_series(db, result.series)
        new_items = _insert_common_news(db, result.news)
        for company in companies:
            # 기존 점수는 건너뛰고 미점수 공통 뉴스만 점수화 —
            # 수집 후 생성된 기업도 기존 뉴스 점수를 보유하게 된다.
            news_n += score_news_for_company(db, company)
        status = "ok" if not errors else "error"
        if not errors and state:
            state.last_success_at = datetime.utcnow()
    except Exception as e:
        status = "error"
        errors.append(f"{collector.name} 수집 예외: {e}")

    now = datetime.utcnow()
    run.status = status
    run.series_count = series_n
    run.news_count = news_n
    run.error = " / ".join(errors)[:2000]
    run.finished_at = now
    if state:
        state.last_run_at = now
        state.next_run_at = datetime.fromtimestamp(
            now.timestamp() + state.interval_sec)
        state.last_error = " / ".join(errors)[:2000]
    db.add(AuditLog(company_id=company_id or 0, user_id=None,
                    user_name="(시스템)", user_role="",
                    action="collection.run", target_type="collector",
                    target_id=collector.name,
                    detail=f"시계열 {series_n}건, 뉴스 점수 {news_n}건, 상태 {status}"))
    db.commit()

    # 신규 중요 데이터 → 기업별 자동 재분석 트리거 (지시서 §18).
    # 동일 입력 데이터의 중복 분석은 파이프라인의 dedup_key가 차단한다.
    if status == "ok" and (series_n > 0 or _has_important_scores(db, companies, new_items)):
        try:
            from .analysis_engine import run_pipeline
            for company in companies:
                run_pipeline(db, company.id, trigger="collect")
            db.commit()
        except Exception as e:
            # 자동 분석 실패가 수집 자체를 실패시키지 않도록 격리
            db.rollback()
            print(f"[collection] 자동 재분석 오류: {e}")

    return {"name": collector.name, "source": collector.source,
            "enabled": True, "series": series_n, "news": news_n,
            "errors": errors, "status": status}


def run_collection(db: Session, company_id: int | None = None,
                   trigger: str = "manual") -> dict:
    """활성 수집기 전체를 실행한다(수동 실행·테스트용). 스케줄러는 due_collectors 사용."""
    ensure_collector_states(db)
    summary = []
    for cls in ALL_COLLECTORS:
        c = cls()
        if not collector_active(c):
            reason = ("비활성 — 이용 조건 미검증(ALLOW_UNVERIFIED_SOURCES=1 필요)"
                      if c.enabled else "비활성 — API 키/설정 없음")
            summary.append({"name": c.name, "source": c.source, "enabled": False,
                            "series": 0, "news": 0,
                            "errors": [reason], "status": "skipped"})
            continue
        summary.append(run_collector(db, c, trigger=trigger,
                                     company_id=company_id))
    return {"ran_at": datetime.utcnow().isoformat(),
            "companies": (1 if company_id else db.query(Company).count()),
            "collectors": summary}


def run_due_collectors(db: Session) -> list[dict]:
    """스케줄러용 — 주기가 도래한 수집기만 실행."""
    return [run_collector(db, c, trigger="schedule")
            for c in due_collectors(db)]


def manual_run_allowed(company_id: int) -> int:
    """수동 실행 가능까지 남은 초. 0이면 즉시 실행 가능."""
    last = _MANUAL_RUN_AT.get(company_id, 0)
    return max(0, int(MANUAL_RUN_COOLDOWN_SEC - (time.time() - last)))


def mark_manual_run(company_id: int) -> None:
    _MANUAL_RUN_AT[company_id] = time.time()
