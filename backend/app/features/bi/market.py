"""Market indicators: free FX rates from Frankfurter (ECB reference rates, no API key)."""

from datetime import date, datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import MarketIndicator

FRANKFURTER_URL = "https://api.frankfurter.dev/v1"
FX_PAIRS = {"USD/KRW": "USD", "JPY/KRW": "JPY", "CNY/KRW": "CNY", "EUR/KRW": "EUR"}


def fetch_fx(codes: list[str], start: date, end: date, client: httpx.Client | None = None) -> list[dict]:
    own = client is None
    client = client or httpx.Client(timeout=15)
    try:
        rows = []
        for code in codes:
            base = FX_PAIRS[code]
            url = f"{FRANKFURTER_URL}/{start.isoformat()}..{end.isoformat()}"
            response = client.get(url, params={"base": base, "symbols": "KRW"})
            response.raise_for_status()
            for day, rates in response.json().get("rates", {}).items():
                rows.append({
                    "code": code, "obs_date": date.fromisoformat(day), "value": float(rates["KRW"]),
                    "source": "Frankfurter (ECB 기준환율)",
                    "source_url": f"{url}?base={base}&symbols=KRW",
                })
        return rows
    finally:
        if own:
            client.close()


def store_indicators(db: Session, rows: list[dict]) -> int:
    """Upsert by (code, obs_date); returns number of new rows."""
    inserted = 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for row in rows:
        existing = db.scalar(select(MarketIndicator).where(
            MarketIndicator.code == row["code"], MarketIndicator.obs_date == row["obs_date"]))
        if existing:
            existing.value, existing.source, existing.source_url = row["value"], row["source"], row["source_url"]
        else:
            db.add(MarketIndicator(collected_at=now, **row))
            inserted += 1
    db.flush()
    return inserted


def collect_fx(db: Session, codes: list[str] | None = None, days: int = 120,
               client: httpx.Client | None = None) -> dict:
    end = date.today()
    rows = fetch_fx(codes or ["USD/KRW", "JPY/KRW", "CNY/KRW"], end - timedelta(days=days), end, client)
    return {"fetched": len(rows), "inserted": store_indicators(db, rows)}


def indicator_series(db: Session, code: str, limit: int = 180) -> list[MarketIndicator]:
    rows = db.scalars(select(MarketIndicator).where(MarketIndicator.code == code)
                      .order_by(MarketIndicator.obs_date.desc()).limit(limit)).all()
    return list(reversed(rows))


def change_over(series: list[MarketIndicator], days: int = 30) -> dict | None:
    """Percent change between the latest value and the value about `days` earlier."""
    if len(series) < 2:
        return None
    latest = series[-1]
    target = latest.obs_date - timedelta(days=days)
    base = next((s for s in reversed(series) if s.obs_date <= target), series[0])
    if base.obs_date == latest.obs_date or not base.value:
        return None
    return {
        "from_date": base.obs_date.isoformat(), "from_value": base.value,
        "to_date": latest.obs_date.isoformat(), "to_value": latest.value,
        "change_pct": round((latest.value - base.value) / base.value * 100, 2),
        "source": latest.source, "source_url": latest.source_url,
    }
