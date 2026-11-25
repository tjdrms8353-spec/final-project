# 데이터 공급처 현황 (DATA_SOURCES)

작성일: 2026-11-25 | 정식 전환 B 보완 기준

## 구현된 수집기

| 수집기 | 공급처 | 제공 데이터 | 인증 | 실연동 상태 | 이용 조건 |
|---|---|---|---|---|---|
| `exim_fx` | 한국수출입은행 | USD/JPY/EUR/CNH 환율 시계열 | `EXIM_API_KEY` | 구현 완료 — 키 발급 대기 (mock 검증) | 검증됨 |
| `ecos_rate` | 한국은행 ECOS | 기준금리(BASE_RATE) 월 시계열 | `ECOS_API_KEY` | 구현 완료 — 키 발급 대기 (mock 검증) | 검증됨 |
| `news_rss` | Google 뉴스 RSS | 뉴스 제목·요약·링크·출처 | 불필요 | **실수집 30건 검증** (단계 B) | ❌ 미검증 → 운영 기본 비활성 |
| `gdelt` | GDELT DOC 2.0 | 전 세계 뉴스 메타데이터 | 불필요 | HTTP 200·기사 수신 확인 — 저장 경로는 공급처 레이트리밋으로 재검증 대기 | 검증됨 |
| `fred` | FRED (연준) | 원/달러(DEXKOUS)·미금리(FEDFUNDS)·WTI(DCOILWTICO) | `FRED_API_KEY` | 구현 완료 — 키 발급 대기 (mock 검증) | 검증됨 |
| `eia` | U.S. EIA v2 | WTI 원유 현물가(RWTC) 월 시계열 | `EIA_API_KEY` | 구현 완료 — 키 발급 대기 (mock 검증) | 검증됨 |
| `dart` | OpenDART | 기업 공시 목록 → 뉴스 항목 매핑 | `DART_API_KEY`+`DART_CORP_CODES` | 구현 완료 — 키·고유번호 대기 (mock 검증) | 검증됨 |

이용 조건 상세: `docs/DATA_LICENSES.md` 참조.

## 저장 구조 (공통 데이터 원칙)

- `market_series`, `news_items`의 공통 외부 데이터는 `company_id=NULL`로 **한 번만** 저장한다.
- 기업별 연결은 `company_news_scores`(관련도·중요도·영향)로 분리 — 기업 수만큼 복제하지 않는다.
- 조회는 `utils.company_or_common()`이 `company_id = 기업 OR NULL`을 병합한다.
- 중복 차단: 시계열은 (series_key, month) 서비스 업서트, 뉴스는 link·제목 dedup.

## 수집기별 스케줄 (`collector_states`)

| 수집기 | 주기 | 근거 |
|---|---|---|
| `exim_fx` | 6시간 | 영업일 일 1회 고시 |
| `ecos_rate` | 24시간 | 월 단위 통계 |
| `news_rss` | 6시간 | 실시간성 뉴스 |
| `gdelt` | 6시간 | 실시간성 뉴스 (5초/요청 제한 준수) |
| `fred` | 24시간 | 일/월 단위 통계 |
| `eia` | 24시간 | 주/월 단위 통계 |
| `dart` | 12시간 | 공시 수시 등록 |

- 상태(`last_run_at`/`last_success_at`/`next_run_at`/`last_error`/`cursor`)와 이력(`collection_runs`)은 DB에 저장.
- 수집 실패 시 마지막 정상 데이터 유지 + `stale` 플래그로 최신성 표시.
- 기업 관리자 수동 실행: 기업당 1시간 1회 제한(429). 스케줄 변경은 환경변수로만(권한 분리).

## 지시서 목록 대비 미구현 공급처

| 공급처 | 상태 | 계획 |
|---|---|---|
| 관세청 수출입무역통계 | 미구현 | 공공데이터포털 키 발급 후 구현 (반도체 수출입 통계) |
| KOSIS | 미구현 | 오픈API 키 발급 후 구현 (광공업생산지수 등 제조업 지표) |
| 정부 보도자료 | 미구현 | 이용 조건 확인 후 GDELT 대체 여부 검토 |

## 반도체·제조업 우선 데이터 매핑

| 필요 데이터 | 현재 공급처 |
|---|---|
| 환율(원/달러·엔·유로·위안) | EXIM, FRED(USD_KRW) |
| 한국·미국 금리 | ECOS(BASE_RATE), FRED(FEDFUNDS) |
| 국제 유가·에너지 가격 | FRED(DCOILWTICO), EIA(RWTC) |
| 기업 공시 | OpenDART |
| 산업 뉴스·정책 | RSS, GDELT |
| 반도체 수출입 통계 | 관세청 API — 미구현(키 대기) |
| 제조업 생산지표 | KOSIS — 미구현(키 대기) |
