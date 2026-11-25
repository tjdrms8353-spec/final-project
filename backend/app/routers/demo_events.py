"""데모 이벤트 — 시장환경 변동 재현 (실제 금융 데이터 아님, 데모 전용)"""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_write
from ..models import DemoEvent, MarketSeries, User
from ..services.analysis_engine import run_pipeline

router = APIRouter(prefix="/api/demo-events", tags=["demo-events"])

# 데모 이벤트 정의: series_key, 증감률, 설명
EVENTS = {
    "fx_spike": {
        "label": "환율 급등 이벤트 (+3.0%)",
        "series_key": "USD_KRW",
        "change_pct": 3.0,
        "description": "원/달러 환율이 단기간 급등하는 상황을 재현합니다. (실제 외환 시세 아님)",
    },
    "rate_hike": {
        "label": "기준금리 인상 이벤트 (+0.5%p)",
        "series_key": "BASE_RATE",
        "change_pct": 0.5,
        "is_additive": True,
        "description": "한국 기준금리가 인상되는 상황을 재현합니다. (실제 금리 아님)",
    },
    "material_surge": {
        "label": "실리콘 웨이퍼 가격 급등 (+8%)",
        "series_key": "SILICON_WAFER",
        "change_pct": 8.0,
        "description": "핵심 원자재 가격이 급등하는 상황을 재현합니다. (실제 시세 아님)",
    },
    "demand_shock": {
        "label": "반도체 수요 둔화 뉴스 이벤트",
        "series_key": None,
        "description": "부정적 산업 뉴스가 등록되며 수요 둔화 리스크를 재현합니다.",
    },
}


@router.get("")
def list_events(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    past = (
        db.query(DemoEvent).filter(DemoEvent.company_id == user.company_id)
        .order_by(DemoEvent.created_at.desc()).limit(20).all()
    )
    return {
        "available": [{"key": k, **{kk: vv for kk, vv in v.items() if kk != "series_key" or True}}
                      for k, v in EVENTS.items()],
        "history": [{"id": e.id, "event_key": e.event_key, "description": e.description,
                     "created_at": e.created_at.isoformat() if e.created_at else ""}
                    for e in past],
        "notice": "데모 이벤트는 테스트용 데이터 변경이며 실제 금융·시장 데이터가 아닙니다.",
    }


@router.post("/{event_key}/run")
def run_event(event_key: str, user: User = Depends(require_write),
              db: Session = Depends(get_db)):
    ev = EVENTS.get(event_key)
    if not ev:
        from fastapi import HTTPException
        raise HTTPException(404, "정의되지 않은 데모 이벤트입니다.")

    cid = user.company_id
    steps = []

    # 1) 시장 시계열에 신규 데이터 포인트 추가 (다음 달 스텝)
    if ev.get("series_key"):
        key = ev["series_key"]
        last = (
            db.query(MarketSeries)
            .filter(MarketSeries.company_id == cid, MarketSeries.series_key == key)
            .order_by(MarketSeries.month.desc()).first()
        )
        if last:
            y, m = map(int, last.month.split("-"))
            m += 1
            if m == 13:
                m, y = 1, y + 1
            new_month = f"{y:04d}-{m:02d}"
            if ev.get("is_additive"):
                new_val = round(last.value + ev["change_pct"], 4)
            else:
                new_val = round(last.value * (1 + ev["change_pct"] / 100), 4)
            db.add(MarketSeries(company_id=cid, series_key=key,
                                series_name=last.series_name, unit=last.unit,
                                source="(데모) 이벤트 생성", month=new_month, value=new_val))
            steps.append(f"1. {last.series_name} 신규 데이터 등록: {new_month} = {new_val}")

    # 수요 둔화 이벤트: 부정 뉴스 추가
    if event_key == "demand_shock":
        from ..models import NewsItem
        n = NewsItem(
            company_id=cid,
            title="[데모 이벤트] 글로벌 반도체 수요 급랭…재고 조정 본격화 우려",
            category="반도체", sentiment="negative", relevance_score=90.0,
            importance="높음",
            impact_on_company="수출 비중이 높은 당사 매출에 직접적인 수요 둔화 압력이 예상됩니다.",
            why_relevant="반도체 산업 수요 사이클은 당사 주요 제품군 수요와 직결됩니다.",
            summary="(데모 이벤트로 생성된 가상 뉴스) 반도체 수요 급랭 시나리오",
            source="(데모) 이벤트 뉴스", published_at=datetime.utcnow(),
        )
        db.add(n)
        steps.append("1. 부정적 산업 뉴스 등록 (수요 둔화 시나리오)")

    db.add(DemoEvent(company_id=cid, event_key=event_key,
                     description=ev["description"], payload=ev))
    db.flush()

    # 2)~8) 분석 파이프라인 실행: KPI 결합 → 시나리오 계산 → 위험 판단 → 알림 → 대시보드 반영 → 이력
    result = run_pipeline(db, cid, trigger=f"demo_event:{event_key}")
    steps.append(f"2~8. 자동 분석 파이프라인 실행 — 분석 {result['new_analyses']}건, "
                 f"신규 위험 알림 {result['new_alerts']}건 생성, 대시보드/알림센터/감사로그 갱신")

    audit(db, user, "DEMO_EVENT", "demo_event", event_key,
          f"{ev['label']} 실행 → {result}")
    db.commit()
    return {"event": ev["label"], "steps": steps, "pipeline": result,
            "notice": "모든 결과는 데모 데이터 기반이며 실제 시장 상황이 아닙니다."}
