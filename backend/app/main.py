import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    APP_ENV, AUTO_ANALYSIS_INTERVAL_SEC, CORS_ORIGINS,
    DEMO_EVENTS_ENABLED, IS_PROD, SEED_DEMO,
)
from .database import Base, SessionLocal, engine
from .models import AnalysisResult, Company
from .routers import (
    alerts, analysis, audit, auth, collection, company, dashboard, decisions,
    demo_events, finance, financial, kpi, news, reports, simulation,
)
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 개발/테스트: create_all로 스키마 자동 생성.
    # 운영: 스키마는 Alembic 마이그레이션이 관리한다 (Dockerfile CMD에서
    # `alembic upgrade head` 선실행) — create_all과 마이그레이션의 충돌 방지.
    if not IS_PROD:
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if SEED_DEMO:
            seeded = seed(db)
            if seeded:
                print("[dayribbon] 데모 데이터 시드 완료")
    finally:
        db.close()

    stop = threading.Event()
    app.state.scheduler_stop = stop
    t = threading.Thread(target=_scheduler_loop, args=(stop,), daemon=True)
    t.start()
    yield
    stop.set()


def _scheduler_loop(stop: threading.Event):
    """경량 자동 분석 스케줄러 (데모용).

    - 매 AUTO_ANALYSIS_INTERVAL_SEC초마다 위험 감지 실행
    - 1분마다 수집기별 스케줄(CollectorState.next_run_at)이 도래한 수집기만 실행
    - 24시간마다 성장/방향성/위험 분석 결과 재생성
    - 신규 알림이 있을 때만 DB에 기록 (중복 알림은 엔진에서 차단)
    """
    last_collect = 0.0
    while not stop.is_set():
        try:
            db = SessionLocal()
            try:
                # 외부 데이터 수집 — 수집기별 스케줄(CollectorState)이 도래한 것만 실행
                if time.time() - last_collect >= 60:
                    from .services.collection_service import run_due_collectors
                    done = run_due_collectors(db)
                    for r in done:
                        print(f"[collector] {r['name']}: 시계열 {r['series']}건 / 뉴스 점수 {r['news']}건")
                    last_collect = time.time()

                cids = [c.id for c in db.query(Company.id).all()]
                for cid in cids:
                    from .services.analysis_engine import detect_risks, weekly_summary
                    from .services.llm_provider import run_analysis
                    detect_risks(db, cid, trigger="schedule")
                    last = (
                        db.query(AnalysisResult.created_at)
                        .filter(AnalysisResult.company_id == cid)
                        .order_by(AnalysisResult.created_at.desc()).first()
                    )
                    stale = last is None or (datetime.utcnow() - last[0]) > timedelta(hours=24)
                    if stale:
                        run_analysis(db, cid, trigger="schedule")
                    # 주간 요약 (7일 중복 차단은 함수 내부에서 처리)
                    weekly_summary(db, cid)
                db.commit()
            finally:
                db.close()
        except Exception as e:
            print(f"[scheduler] 오류: {e}")
        stop.wait(AUTO_ANALYSIS_INTERVAL_SEC)


app = FastAPI(
    title="dayribbon BI API",
    description="AI 기반 중소기업형 맞춤형 BI 시스템",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in CORS_ORIGINS.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth.auth_router, company.company_router, dashboard.router,
          financial.router, news.router, finance.router, analysis.router,
          simulation.router, alerts.router, decisions.router,
          reports.router, audit.router, collection.router, kpi.router):
    app.include_router(r)

# 데모 전용 라우터 — DEMO_EVENTS_ENABLED=1 일 때만 노출 (실데이터 오염 방지)
if DEMO_EVENTS_ENABLED:
    app.include_router(demo_events.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "dayribbon",
            "env": APP_ENV,
            "mode": "demo (rule-based analysis)" if SEED_DEMO else "service",
            "time": datetime.utcnow().isoformat()}


@app.get("/api/health/db")
def health_db():
    """DB 연결 상태 확인 — 운영 모니터링용."""
    from .database import check_db
    r = check_db()
    if not r["ok"]:
        from fastapi import HTTPException
        raise HTTPException(503, f"DB 연결 실패: {r.get('error', '')[:200]}")
    return {"status": "ok", **r}
