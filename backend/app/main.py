import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import (
    AUTO_ANALYSIS_INTERVAL_SEC, CORS_ORIGINS, DEMO_EVENTS_ENABLED, SEED_DEMO,
)
from .database import Base, SessionLocal, engine
from .models import AnalysisResult, Company
from .routers import (
    alerts, analysis, audit, auth, company, dashboard, decisions,
    demo_events, finance, financial, news, reports, simulation,
)
from .seed import seed


@asynccontextmanager
async def lifespan(app: FastAPI):
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
    - 24시간마다 성장/방향성/위험 분석 결과 재생성
    - 신규 알림이 있을 때만 DB에 기록 (중복 알림은 엔진에서 차단)
    """
    while not stop.is_set():
        try:
            db = SessionLocal()
            try:
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
    title="dayribbon BI Demo API",
    description="AI 기반 중소기업형 맞춤형 BI 시스템 — 데모 버전 (규칙 기반 분석)",
    version="0.1.0",
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
          reports.router, audit.router):
    app.include_router(r)

# 데모 전용 라우터 — DEMO_EVENTS_ENABLED=1 일 때만 노출 (실데이터 오염 방지)
if DEMO_EVENTS_ENABLED:
    app.include_router(demo_events.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "dayribbon-bi-demo",
            "mode": "demo (rule-based analysis)", "time": datetime.utcnow().isoformat()}
