"""운영 상태 API — 스케줄러·수집기·발송·LLM·분석 작업의 현황을 한곳에서 확인."""
import os
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..config import APP_ENV, AUTO_ANALYSIS_INTERVAL_SEC
from ..database import get_db
from ..deps import require_admin
from ..models import (
    AnalysisJob, CollectionRun, CollectorState, LlmCall, NotificationDelivery,
    User,
)

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/status")
def ops_status(user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """관리자용 운영 상태 — 스케줄러·수집·발송·LLM 사용량·분석 작업 집계."""
    month_start = datetime.utcnow().strftime("%Y-%m-01")

    deliveries = dict(
        db.query(NotificationDelivery.status, func.count())
        .group_by(NotificationDelivery.status).all())   # 전사 범위(기업 미소속 건 포함)

    collectors = db.query(CollectorState).all()
    recent_failed_runs = (db.query(CollectionRun)
                          .filter(CollectionRun.status == "error")
                          .order_by(CollectionRun.started_at.desc()).limit(5).all())

    llm = db.query(func.count(LlmCall.id),
                   func.coalesce(func.sum(LlmCall.prompt_tokens + LlmCall.completion_tokens), 0)) \
        .filter(LlmCall.company_id == user.company_id,
                LlmCall.created_at >= month_start).first()

    jobs = dict(
        db.query(AnalysisJob.status, func.count())
        .filter(AnalysisJob.company_id == user.company_id)
        .group_by(AnalysisJob.status).all())

    from ..services.delivery_service import email_configured, kakao_configured, resend_configured
    return {
        "env": APP_ENV,
        "version": os.getenv("RENDER_GIT_COMMIT", "")[:7] or "local",
        "server_time": datetime.utcnow().isoformat(),
        "scheduler_interval_sec": AUTO_ANALYSIS_INTERVAL_SEC,
        "deliveries": {
            "pending": deliveries.get("pending", 0),
            "sent": deliveries.get("sent", 0),
            "failed": deliveries.get("failed", 0),
            "skipped": deliveries.get("skipped", 0),
            "email_configured": email_configured(),
            "resend_configured": resend_configured(),
            "kakao_configured": kakao_configured(),
        },
        "collectors": {
            "total": len(collectors),
            "enabled": sum(1 for c in collectors if c.enabled),
            "list": [
                {"name": c.name, "enabled": c.enabled,
                 "interval_sec": c.interval_sec,
                 "last_run_at": c.last_run_at.isoformat() if c.last_run_at else "",
                 "last_success_at": c.last_success_at.isoformat() if c.last_success_at else "",
                 "next_run_at": c.next_run_at.isoformat() if c.next_run_at else "",
                 "last_error": (c.last_error or "")[:120]}
                for c in collectors],
            "recent_errors": [
                {"collector": r.collector, "at": r.started_at.isoformat(),
                 "error": (r.error or "")[:120]}
                for r in recent_failed_runs],
        },
        "llm_month": {"calls": llm[0], "tokens": llm[1]},
        "analysis_jobs": jobs,
    }


class TestDelivery(BaseModel):
    channel: str = Field(pattern="^(email|kakao)$")
    address: str = Field(min_length=3, max_length=200)


@router.post("/test-delivery")
def test_delivery(body: TestDelivery, user: User = Depends(require_admin),
                  db: Session = Depends(get_db)):
    """관리자 테스트 발송 — 큐에 적재 후 즉시 처리해 결과를 바로 확인한다."""
    from ..services.delivery_service import (
        enqueue_delivery, process_pending_deliveries)
    d = enqueue_delivery(
        db, user.company_id, body.channel, body.address,
        "발송 테스트",
        "운영 상태 화면에서 발송한 테스트 메시지입니다.")
    db.flush()
    process_pending_deliveries(db)   # 즉시 발송 시도
    db.commit()
    return {"id": d.id, "status": d.status, "last_error": d.last_error,
            "note": "미설정 채널이면 발송 대기로 남습니다."}
