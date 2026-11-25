"""해외·공시 수집 어댑터 (정식 전환 B 보완).

- GdeltNewsCollector : GDELT DOC 2.0 API — 오픈 데이터, 키 불필요, 실수집 동작
- FredSeriesCollector : FRED — 원/달러(DEXKOUS)·미 기준금리(FEDFUNDS)·WTI(DCOILWTICO), FRED_API_KEY 필요
- EiaSeriesCollector : EIA v2 — WTI 현물가(RWTC), EIA_API_KEY 필요
- DartDisclosureCollector : OpenDART — 기업 공시 목록, DART_API_KEY + DART_CORP_CODES 필요

키가 없으면 enabled=False이며 collect()는 빈 결과를 반환한다.
"""
from datetime import datetime

from ...config import (
    DART_API_KEY, DART_CORP_CODES, EIA_API_KEY, FRED_API_KEY, GDELT_ENABLED,
    IS_PROD,
)
from .base import CollectorResult, get_json

# 공급처별 이용 조건 검증 여부 — 미검증 소스는 운영에서 기본 비활성
# (docs/DATA_LICENSES.md 참조, ALLOW_UNVERIFIED_SOURCES=1로 강제 가능)


class GdeltNewsCollector:
    """GDELT DOC 2.0 — 전 세계 뉴스 메타데이터 (오픈 데이터, 출처 표기 권장).

    license_verified: GDELT Terms는 비상업·상업 모두 자유 이용+출처 표기를 허용
    (https://www.gdeltproject.org/about.html#termsofuse).
    """

    name = "gdelt"
    source = "GDELT Project"
    license_verified = True
    URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    QUERY = 'sourcelang:korean (반도체 OR 환율 OR 수출입 OR 원자재 OR 금리)'

    @property
    def enabled(self) -> bool:
        return GDELT_ENABLED

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        try:
            data = get_json(self.URL, params={
                "query": self.QUERY, "mode": "artlist",
                "maxrecords": "40", "timespan": "1d", "format": "json",
            })
        except Exception as e:
            res.errors.append(str(e))
            return res
        for a in (data or {}).get("articles", []):
            seen = str(a.get("seendate", ""))           # "20261124T120000Z"
            try:
                published = datetime.strptime(seen[:15], "%Y%m%dT%H%M%S")
            except ValueError:
                published = datetime.utcnow()
            res.news.append({
                "title": (a.get("title") or "").strip()[:490],
                "summary": "",                          # artlist는 요약 미제공
                "source": a.get("domain", "GDELT"),
                "link": a.get("url", ""),
                "published_at": published,
            })
        if not res.news:
            res.errors.append("GDELT 응답에 기사가 없습니다(쿼리·기간 조건 확인)")
        return res


# FRED 시계열: series_id → (series_key, 이름, 단위)
FRED_SERIES = {
    "DEXKOUS": ("USD_KRW", "원/달러 환율(FRED)", "KRW"),
    "FEDFUNDS": ("FED_RATE", "미국 연방기금 금리", "%"),
    "DCOILWTICO": ("WTI_OIL", "WTI 국제유가(FRED)", "$/bbl"),
}


class FredSeriesCollector:
    """FRED (St. Louis Fed) — 미국 공공 경제 데이터. 무료 키 필요.

    license_verified: 공공기관 데이터, 출처 표기 조건으로 이용 가능
    (https://fred.stlouisfed.org/docs/api/terms_of_use.html).
    """

    name = "fred"
    source = "FRED (Federal Reserve Bank of St. Louis)"
    license_verified = True
    URL = "https://api.stlouisfed.org/fred/series/observations"

    @property
    def enabled(self) -> bool:
        return bool(FRED_API_KEY)

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("FRED_API_KEY 미설정 — 수집 비활성")
            return res
        for series_id, (key, name, unit) in FRED_SERIES.items():
            try:
                data = get_json(self.URL, params={
                    "series_id": series_id, "api_key": FRED_API_KEY,
                    "file_type": "json", "sort_order": "desc", "limit": "12",
                })
            except Exception as e:
                res.errors.append(f"{series_id}: {e}")
                continue
            for obs in (data or {}).get("observations", []):
                try:
                    value = float(obs.get("value", "."))
                except ValueError:
                    continue
                d = str(obs.get("date", ""))             # "2026-11-01"
                res.series.append({
                    "series_key": key, "series_name": name, "unit": unit,
                    "month": d[:7], "value": value,
                })
        return res


class EiaSeriesCollector:
    """EIA v2 — WTI 원유 현물가 (미국 에너지정보청, 공공데이터). EIA_API_KEY 필요.

    license_verified: 미국 정부 공공데이터 (https://www.eia.gov/about/copyrights_reuse.php).
    """

    name = "eia"
    source = "U.S. EIA"
    license_verified = True
    URL = "https://api.eia.gov/v2/petroleum/pri/spt/data/"

    @property
    def enabled(self) -> bool:
        return bool(EIA_API_KEY)

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("EIA_API_KEY 미설정 — 수집 비활성")
            return res
        try:
            data = get_json(self.URL, params={
                "api_key": EIA_API_KEY, "frequency": "monthly",
                "facets[series][]": "RWTC",
                "data[0]": "value", "sort[0][column]": "period",
                "sort[0][direction]": "desc", "length": "12",
            })
        except Exception as e:
            res.errors.append(str(e))
            return res
        for row in ((data or {}).get("response") or {}).get("data", []):
            try:
                value = float(row.get("value"))
            except (TypeError, ValueError):
                continue
            res.series.append({
                "series_key": "WTI_OIL", "series_name": "WTI 현물가(EIA)",
                "unit": "$/bbl", "month": str(row.get("period", ""))[:7],
                "value": value,
            })
        if not res.series:
            res.errors.append("EIA 응답에 데이터가 없습니다")
        return res


class DartDisclosureCollector:
    """OpenDART — 기업 공시 목록 (금융감독원 전자공시). DART_API_KEY 필요.

    corp_code는 DART 고유번호로 DART_CORP_CODES에 쉼표로 지정한다.
    공시를 뉴스 항목으로 매핑해 기업 모니터링에 활용한다.

    license_verified: 공공데이터포털 오픈API (이용 조건: 출처 표기).
    """

    name = "dart"
    source = "OpenDART (금융감독원)"
    license_verified = True
    URL = "https://opendart.fss.or.kr/api/list.json"

    @property
    def enabled(self) -> bool:
        return bool(DART_API_KEY and DART_CORP_CODES.strip())

    def collect(self) -> CollectorResult:
        res = CollectorResult(source=self.source,
                              fetched_at=datetime.utcnow().isoformat())
        if not self.enabled:
            res.errors.append("DART_API_KEY 또는 DART_CORP_CODES 미설정 — 수집 비활성")
            return res
        codes = [c.strip() for c in DART_CORP_CODES.split(",") if c.strip()]
        today = datetime.utcnow()
        for code in codes[:20]:  # 호출 제한 보호 — 최대 20개 기업
            try:
                data = get_json(self.URL, params={
                    "crtfc_key": DART_API_KEY, "corp_code": code,
                    "bgn_de": (today.replace(day=1)).strftime("%Y%m%d"),
                    "end_de": today.strftime("%Y%m%d"),
                    "page_count": "20",
                })
            except Exception as e:
                res.errors.append(f"{code}: {e}")
                continue
            for item in (data or {}).get("list", []):
                d = str(item.get("rcept_dt", ""))
                try:
                    published = datetime.strptime(d, "%Y%m%d")
                except ValueError:
                    published = today
                res.news.append({
                    "title": f"[공시] {item.get('corp_name','')} — {item.get('report_nm','')}"[:490],
                    "summary": f"{item.get('corp_name','')}의 공시({item.get('report_nm','')}), "
                               f"제출인: {item.get('flr_nm','')}",
                    "source": "OpenDART (금융감독원)",
                    "link": (f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={item.get('rcept_no','')}"
                             if item.get("rcept_no") else ""),
                    "published_at": published,
                })
        return res
