"""환율/금리 수집 어댑터 — 한국수출입은행 EXIM + 한국은행 ECOS.

- EXIM: https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON
  (무료. 일일 매매기준율. 월 단위 시계열에 "당월 최신값"으로 기록한다)
- ECOS: https://ecos.bok.or.kr/api/StatisticSearch (기준금리, 월 단위)

두 API 모두 키가 없으면 enabled=False이며 collect()는 빈 결과를 반환한다.
HTTP 호출은 base.get_json으로 통일 — 테스트에서 교체해 검증한다.
"""
from datetime import datetime

from ...config import ECOS_API_KEY, EXIM_API_KEY
from .base import CollectorResult, get_json

EXIM_URL = "https://oapi.koreaexim.go.kr/site/program/financial/exchangeJSON"

# EXIM cur_unit → (series_key, series_name, unit)
FX_MAP = {
    "USD": ("USD_KRW", "원/달러 환율", "KRW"),
    "JPY(100)": ("JPY_KRW", "원/엔 환율(100엔)", "KRW"),
    "EUR": ("EUR_KRW", "원/유로 환율", "KRW"),
    "CNH": ("CNY_KRW", "원/위안 환율", "KRW"),
}

# ECOS 기준금리: 722Y001(한국은행 기준금리) / 010100000(기준금리), 월 단위
ECOS_STAT_URL = "https://ecos.bok.or.kr/api/StatisticSearch"
ECOS_BASE_RATE = ("722Y001", "010100000")


class EximFxCollector:
    name = "exim_fx"
    source = "한국수출입은행 EXIM"

    @property
    def enabled(self) -> bool:
        return bool(EXIM_API_KEY)

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("EXIM_API_KEY 미설정 — 수집 비활성")
            return res
        today = datetime.utcnow()
        try:
            data = get_json(EXIM_URL, params={
                "authkey": EXIM_API_KEY,
                "searchdate": today.strftime("%Y%m%d"),
                "data": "AP01",
            })
        except Exception as e:
            res.errors.append(str(e))
            return res
        if not isinstance(data, list):
            res.errors.append(f"EXIM 응답 형식 오류: {str(data)[:100]}")
            return res
        month = today.strftime("%Y-%m")
        for row in data:
            mapped = FX_MAP.get(str(row.get("cur_unit", "")))
            if not mapped:
                continue
            try:
                value = float(str(row.get("deal_bas_r", "")).replace(",", ""))
            except ValueError:
                continue
            key, name, unit = mapped
            res.series.append({"series_key": key, "series_name": name,
                               "unit": unit, "month": month, "value": value})
        if not res.series:
            res.errors.append("EXIM 응답에 수집 가능한 통화가 없습니다(휴일·비영업일 가능)")
        return res


class EcosRateCollector:
    name = "ecos_rate"
    source = "한국은행 ECOS"

    @property
    def enabled(self) -> bool:
        return bool(ECOS_API_KEY)

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("ECOS_API_KEY 미설정 — 수집 비활성")
            return res
        now = datetime.utcnow()
        end = now.strftime("%Y%m")
        start = f"{now.year - 1}{now.month:02d}"
        stat_code, item_code = ECOS_BASE_RATE
        url = (f"{ECOS_STAT_URL}/{ECOS_API_KEY}/json/kr/1/24/"
               f"{stat_code}/M/{start}/{end}/{item_code}")
        try:
            data = get_json(url)
        except Exception as e:
            res.errors.append(str(e))
            return res
        rows = (data.get("StatisticSearch") or {}).get("row") or []
        for row in rows:
            t = str(row.get("TIME", ""))          # "202401"
            try:
                value = float(row.get("DATA_VALUE"))
            except (TypeError, ValueError):
                continue
            if len(t) != 6:
                continue
            res.series.append({
                "series_key": "BASE_RATE", "series_name": "한국은행 기준금리",
                "unit": "%", "month": f"{t[:4]}-{t[4:]}", "value": value,
            })
        if not res.series:
            res.errors.append(f"ECOS 응답에 데이터가 없습니다: {str(data)[:150]}")
        return res
