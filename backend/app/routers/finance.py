"""금융 및 경제 데이터 — 시계열 지표 + 기업 영향 설명"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Company, MarketSeries, User

router = APIRouter(prefix="/api/finance", tags=["finance"])

# 지표별 기업 영향 설명 (규칙 기반, 데모)
IMPACT_NOTES = {
    "USD_KRW": "환율 상승은 원자재 등 수입 비용을 증가시키고, 하락은 수출가격 경쟁력을 높입니다. 외화 결제 비중이 높을수록 민감도가 큽니다.",
    "BASE_RATE": "기준금리 상승은 차입금 이자 부담을 키우고, 인하 시 금융비용이 줄어듭니다.",
    "FED_RATE": "미국 금리 변화는 달러 강세·환율과 글로벌 수요 심리에 영향을 줍니다.",
    "KOSPI": "국내 증시 흐름은 투자심리와 수출 기업 밸류에이션에 간접 영향을 줍니다.",
    "NASDAQ": "나스닥은 글로벌 기술주 심리의 바로미터로, 반도체 업황 선행지표로 참고됩니다.",
    "SEMI_ETF": "반도체 업종 지수는 산업 수요 사이클을 반영하며 당사 제품 수요와 상관관계가 있습니다.",
    "WTI_OIL": "유가 상승은 에너지·물류 비용을 통해 제조 간접비를 높입니다.",
    "COPPER": "구리는 전자부품·기판의 핵심 원자재로 가격 상승 시 원가율에 직접 영향을 줍니다.",
    "SILICON_WAFER": "실리콘 웨이퍼는 최대 원자재로, 가격 상승 시 원가율 악화가 직접적입니다.",
}


@router.get("/series")
def list_series(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(MarketSeries)
        .filter(MarketSeries.company_id == user.company_id)
        .order_by(MarketSeries.series_key, MarketSeries.month)
        .all()
    )
    grouped: dict[str, dict] = {}
    for r in rows:
        g = grouped.setdefault(r.series_key, {
            "series_key": r.series_key, "series_name": r.series_name,
            "unit": r.unit, "source": r.source, "impact_note": IMPACT_NOTES.get(r.series_key, ""),
            "points": [],
        })
        g["points"].append({"month": r.month, "value": r.value})
    out = []
    for g in grouped.values():
        pts = g["points"]
        if len(pts) >= 2:
            last, prev = pts[-1]["value"], pts[-2]["value"]
            g["latest"] = last
            g["previous"] = prev
            g["change_pct"] = round((last - prev) / abs(prev) * 100, 2) if prev else None
        else:
            g["latest"] = pts[-1]["value"] if pts else None
            g["previous"] = None
            g["change_pct"] = None
        out.append(g)
    return out


@router.get("/series/{series_key}")
def get_series(series_key: str, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    rows = (
        db.query(MarketSeries)
        .filter(MarketSeries.company_id == user.company_id,
                MarketSeries.series_key == series_key)
        .order_by(MarketSeries.month).all()
    )
    if not rows:
        from fastapi import HTTPException
        raise HTTPException(404, "해당 지표를 찾을 수 없습니다.")
    return {
        "series_key": series_key,
        "series_name": rows[0].series_name,
        "unit": rows[0].unit,
        "source": rows[0].source,
        "impact_note": IMPACT_NOTES.get(series_key, ""),
        "points": [{"month": r.month, "value": r.value} for r in rows],
    }
