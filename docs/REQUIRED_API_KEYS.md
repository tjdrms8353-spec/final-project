# 필요한 API 키·외부 설정 (REQUIRED_API_KEYS)

작성일: 2026-11-25

> 모든 키는 USB의 `.env`에만 보관한다. Git·로컬 작업공간에 커밋하지 않는다.
> 키가 없으면 해당 수집기/기능은 `enabled=False`로 동작하고 Mock 테스트로 검증된다.

## 데이터 수집

| 변수 | 공급처 | 발급처 | 비용 | 현재 상태 |
|---|---|---|---|---|
| `EXIM_API_KEY` | 한국수출입은행 환율 | oapi.koreaexim.go.kr | 무료 | 대기 |
| `ECOS_API_KEY` | 한국은행 ECOS | ecos.bok.or.kr | 무료 | 대기 |
| `FRED_API_KEY` | FRED 연준 데이터 | fred.stlouisfed.org | 무료 | 대기 |
| `EIA_API_KEY` | 미국 에너지정보청 | eia.gov | 무료 | 대기 |
| `DART_API_KEY` | OpenDART 공시 | opendart.fss.or.kr | 무료 | 대기 |
| `DART_CORP_CODES` | DART 고유번호 목록 | opendart 고유번호 다운로드 | 무료 | 대기 (키와 함께 필요) |
| `NEWS_API_KEY` | 뉴스 검색 API(보강용) | — | — | 선택 사항 (RSS/GDELT로 기본 동작) |
| — | GDELT | 불필요 | 무료(오픈 데이터) | 구현 완료, `GDELT_ENABLED`로 제어 |

## LLM 분석

| 변수 | 용도 | 비고 |
|---|---|---|
| `LLM_API_KEY` | 외부 LLM 인증 | 미설정 시 규칙 기반 엔진만 사용 |
| `LLM_BASE_URL` | OpenAI 호환 엔드포인트 (예: `http://localhost:11434/v1` 또는 공급처 URL) | 특정 공급처 종속 없음 |
| `LLM_MODEL` | 모델명 | 무료/저비용 모델 우선 검토 — 임의 유료 가입 금지 |
| `LLM_TIMEOUT_SEC` | 호출 타임아웃 (기본 30) | 선택 |
| `LLM_MAX_RETRIES` | 재시도 횟수 (기본 1) | 선택 |
| `LLM_MONTHLY_TOKEN_BUDGET` | 기업당 월 토큰 예산 (기본 0=무제한) | 초과 시 자동 폴백 |

추가 조건: 외부 LLM 호출은 **기업별 `allow_external_ai` 옵트인**이 필요하다
(기업 설정 화면 토글, 기본 OFF).

## 데이터베이스

| 변수 | 용도 | 상태 |
|---|---|---|
| `DATABASE_URL` | TiDB/MySQL 접속 (`mysql+pymysql://...`) | 대기 — 개발은 SQLite |
| `DB_SSL_CA` | TiDB Cloud TLS CA 파일 경로 | 대기 |
| `DB_POOL_SIZE` / `DB_POOL_RECYCLE` | 커넥션 풀 | 선택 |

## 기타

| 변수 | 용도 | 상태 |
|---|---|---|
| `ALLOW_UNVERIFIED_SOURCES` | 이용 조건 미검증 공급처(Google 뉴스 RSS)를 production에서 강제 활성화 — 기본 0 | 선택 |
| 이메일/카카오 발송 | 알림 실발송 | 단계 D 범위 — 대기 |
