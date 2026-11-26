# dayribbon 개발 진행 기록

> `docs/DEVELOPMENT_PLAN.md`의 20단계 계획을 추적합니다.
> 작업자는 매 단계 종료 시 이 문서를 즉시 갱신합니다.

## 전체 진행률

- 완료: 20 / 20단계 — 이후 Phase A~E(정식 전환)는 `DEVELOPMENT_PLAN.md` 참조

## 완료된 단계 (1~15)

| 단계 | 내용 | 검증 |
|---|---|---|
| 1 | 데모 프로젝트 구조·독립 환경 | 폴더/스크립트/문서 생성 완료 |
| 2 | DB 스키마·모델 | 18 테이블, startup create_all |
| 3 | 데모 데이터 시드 | 24개월 재무/시계열/뉴스/분석/보고서/결정·조치 |
| 4 | 인증·권한 | 로그인 토큰, 4역할, 쓰기 API 403 확인 |
| 5 | 조회 API | 대시보드·뉴스·금융·기업·사용자 정상 |
| 6 | 업로드 | CSV/Excel 검증·upsert·자동분석 트리거 |
| 7 | 규칙 분석 엔진 | 3영역 결과 생성·검토 상태·면책 명시 |
| 8 | 시뮬레이션 | 변수→영향·등급·가정 명시 실측 |
| 9 | 자동 분석·알림 | 업로드/이벤트/스케줄 트리거, 중복 알림 차단 |
| 10 | 의사결정·후속조치 | 생성/변경/이력/분석 상태 연동 |
| 11 | 보고서·PDF | 한글 PDF 생성·다운로드 실측 |
| 12 | 감사 로그 | 자동 기록·읽기 전용·필터 |
| 13 | 프론트엔드 | 13 라우트 전체 실데이터 렌더링 확인 |
| 14 | 스크립트·README | setup/start/stop ps1·sh, README |
| 15 | 통합 검증 | `fmtDate` 누락·`Card` props·`get_current_user` 누락 수정 |

## 진행 중 — 이번 세션 작업 범위 (16~19)

| 단계 | 항목 | 진행 |
|---|---|---|
| 16 | AGENTS.md, DEVELOPMENT_PLAN.md, 본 문서 | ✅ 완료 |
| 17 | pytest API 테스트 코드 22건 (전체 통과) | ✅ 완료 |
| 18 | 토큰 해시 저장, 로그인 실패 잠금, 업로드 용량 제한 | ✅ 완료 |
| 19 | "분석 완료"·주간 요약 알림 발행, 제품/거래처/원자재 CRUD | ✅ 완료 (업로드 미리보기 2단계는 단계 20으로 이월) |

## 미완료·알려진 한계 (정식 전환 대상)

- 실제 뉴스·금융 데이터 수집(외부 API) — 시드 데이터 사용 중
- LLM 기반 분석 — 규칙 기반 엔진으로 동작 중(화면에 명시)
- 실제 이메일/카카오 발송 — 발송 대기 큐만
- TiDB 전환 — SQLite 사용 중(ORM 분리로 대비)
- 온보딩(회원가입·기업생성·초대)
- ERP 연동 — 별도 프로젝트, 계약만 정의 예정
- PDF/OCR 업로드 — 미구현 명시
- 업로드 미리보기 2단계 플로우 — 단계 20으로 이월
- 멀티 워커 스케줄러 안전성(APScheduler/잡스토어)
- 배포 구성(Dockerfile/CI) — 없음

## 작업 이력

- 2026-11-25 (1차): 단계 1~15 완료 — 데모 전체 구현·검증·커밋
- 2026-11-25 (2차): 대시보드 `fmtDate` 누락·`Card` props·`demo_events` import 누락 수정 + `ErrorBoundary` 추가 + 전환 분석 보고서 작성
- 2026-11-25 (3차): 단계 16~19 진행 — 개발 문서 체계·테스트·보안·기능 보완

---

## 2026-11-25 (3차) 작업 상세 — 단계 16~19

### 완료 사항
- **문서 체계(16)**: `AGENTS.md`, `docs/DEVELOPMENT_PLAN.md`(20단계), `DEVELOPMENT_PROGRESS.md` 신설
- **테스트(17)**: `backend/tests/` pytest 22건 구축 — 인증/권한/재무CRUD/제품·거래처·원자재CRUD/업로드(검증·용량제한)/대시보드/알림설정/주간요약/감사로그/시뮬레이션. **전체 통과(22/22)**
- **보안(18)**:
  - 토큰 해시 저장(`hash_token` — DB 유출 시 원문 복원 불가), 로그인·me·logout 모두 해시 조회로 전환
  - 로그인 실패 5회 → 15분 잠금(429, 인메모리)
  - 업로드 20MB 용량 제한(413)
- **기능(19)**:
  - 알림 설정 게이팅 실제 적용: `risk_alert`/`important_news`/`kpi_change`/`analysis_done` 플래그가 알림 발행을 제어
  - "분석 완료" 알림 발행(`run_pipeline`), "주간 요약" 알림(`weekly_summary` + 스케줄러 연동, 7일 중복 차단)
  - 제품/거래처/원자재 CRUD API(`/api/financial/records/{kind}` 목록·upsert·삭제)
  - 프론트엔드 `InternalData` 페이지에 "제품·거래처·원자재" 탭 신설(직접 입력·목록·삭제)
- 프론트엔드 빌드 검증 통과(646 모듈, dist-verify 출력)

### 주의/미해결
- `frontend/dist` 폴더에 ACL 손상(삭제 불가) — 빌드 산출물이라 동작 무관, `--outDir`로 우회 검증. 환경 문제로 추후 OS 재부팅/관리자 권한 필요 가능성 있음
- `requirements.txt`에 pytest·httpx 추가됨 (테스트 의존성)
- 기존 세션 토큰은 해시 적용으로 무효화 — 재로그인 필요
- 업로드 "미리보기 2단계" 플로우는 다음 단계(20)로 이월

---

## 2026-11-25 (4차) 작업 상세 — 단계 20 (정식 전환 준비)

### 완료 사항
- **환경변수화**: `VITE_API_BASE`로 API 베이스 주소 분리(빌드 후 직접 호출 지원), `TOKEN_TTL_HOURS`·`DEMO_EVENTS_ENABLED` env화
- **보안 정리**: 미사용 하드코딩 `SECRET_KEY` 제거(코드에서 실제 미사용 확인 후 삭제)
- **데모 라우터 격리**: `demo_events` 라우터를 `DEMO_EVENTS_ENABLED` 플래그로 게이트 — 실서비스에서 0 설정 시 노출 차단
- **LLM 인터페이스**: `services/llm_provider.py` — `run_analysis()` 진입점(LLM 우선·실패 시 규칙 엔진 폴백), 파이프라인·스케줄러 모두 이 경로로 통일. env: `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL`
- **수집 어댑터 골격**: `services/collectors/` — `Collector`/`CollectorResult` 공통 인터페이스 + EXIM 환율·ECOS 금리·뉴스 스텁(API 키 미설정 시 `enabled=False`, Phase B에서 실구현)
- **업로드 미리보기 2단계**: `POST /api/financial/upload/preview`(검증만, 저장 없음) + `_prepare_df`로 검증 로직 공유 + 프론트 "1.미리보기 → 2.업로드 확정" 플로우(상위 10행·경고 표시)
- **배포 구성**: `backend/Dockerfile`, `frontend/Dockerfile`(nginx + `/api` 프록시), `nginx.conf`, `docker-compose.yml`, `.dockerignore`
- **TiDB 대비**: `.env.example`에 `mysql+pymysql://` 예시·수집/LLM 키 문서화, requirements에 pymysql·alembic 주석 추가

### 검증
- pytest **23/23 통과** (미리보기 비저장 검증 테스트 추가)
- 프론트엔드 빌드 통과 (dist-verify 출력 후 삭제)

### 20단계 계획 전체 완료
- 1~15 데모 구현, 16 문서 체계, 17 테스트, 18 보안, 19 기능 보완, 20 전환 준비
- 이후 작업은 `DEVELOPMENT_PLAN.md`의 Phase A~E(정식 전환)로 진행

---

# 정식 전환 작업 기록 (dayribbon 정식 프로젝트)

> 원본 데모 `dayribbon-bi-demo` 보존, 정식 프로젝트 `dayribbon`에서 진행.
> 20단계 데모 계획과 별개 번호: 전환 단계 A~E (`PRODUCTION_PLAN_A.md`)

## 2026-11-25 — 전환 단계 A: 기반 시스템 구축 [완료]

### 환경 분리
- 정식 프로젝트: `E:\송성근(심화)\dayribbon\dayribbon` (독립 git, main 브랜치)
- 원본 데모 `dayribbon-bi-demo` 미수정 보존, ERP 프로젝트 무수정
- E: 드라이브 여유공간 0으로 백엔드 venv는 `C:\venvs\dayribbon`에 설치
  (테스트 명령: `C:/venvs/dayribbon/Scripts/python.exe -m pytest tests`)
- 프론트 빌드 검증은 `C:\dayribbon-build` 작업공간(node_modules junction)에서 수행

### DB (TiDB 준비)
- `pymysql`·`alembic` 의존성 실제 추가(requirements.txt)
- `database.py`: 비-sqlite 시 pool_size/pool_recycle/pool_pre_ping, `DB_SSL_CA` TLS
- `GET /api/health/db` — SELECT 1 기반 연결 상태 API
- `APP_ENV=production` 시 DATABASE_URL 미설정·sqlite 지정이면 RuntimeError로 시작 거부
- production 기본값: SEED_DEMO·DEMO_EVENTS_ENABLED 자동 비활성
- Alembic 초기화 + 최초 마이그레이션 `033a6f74f669 initial schema` (22테이블)
  — upgrade→downgrade→upgrade SQLite 검증 통과. TiDB 실접속은 접속 정보 대기(외부 설정)
- 금액 컬럼 Float 유지 결정: float64 유효자릿수(~15자리)가 현재 규모(조 단위 원화)에 충분.
  Decimal(Numeric(20,2)) 전환은 데이터 규모 확대 시 별도 마이그레이션으로 검토

### 인증
- POST /api/auth/register (이메일 중복 409, 비밀번호 min 8, 기업 미소속 생성)
- POST /api/auth/change-password (현재 비밀번호 검증, 기존 세션 전체 무효화)
- POST /api/auth/password-reset/request + /confirm (해시 토큰·1회용·1시간 만료,
  이메일 미연동으로 데모 토큰 응답 포함 — 발송 연동 시 제거)
- 기존 유지: 토큰 해시 저장·만료·로그아웃 무효화·로그인 5회 잠금

### 워크스페이스·권한
- memberships 테이블 (user↔company M:N, 유니크 제약)
- users.company_id → 활성 기업 포인터(nullable, 회원가입 직후 NULL)
- Company 모델 데모 기본값 제거 — 신규 기업 빈 상태 시작
- POST /api/companies (기업 등록 → OWNER 소속·알림설정 생성, 데모 데이터 미생성)
- GET /api/companies/mine, POST /api/companies/select (소속 검증 필수)
- company_invites: 생성(ADMIN+, OWNER 초대 불가)·목록·취소·수락(이메일 일치 검증)·만료
- PUT /api/users/{id} OWNER 보호(OWNER 변경·부여는 OWNER만), DELETE 접근 해제
- require_write에 소속 기업 필수 가드, 감사로그 company_id NULL 안전 처리

### 프론트엔드
- Signup.jsx, Onboarding.jsx (기업 등록·초대 수락·소속 기업 선택)
- RequireAuth: company_id 없으면 /onboarding 리다이렉트
- Login: /api/health mode 기반 데모 계정 표시(운영에서 미노출), 회원가입 링크
- Settings 사용자 탭: 워크스페이스 전환·초대 생성/목록/취소·권한 변경·접근 해제

### 테스트·검증
- pytest 39/39 통과 (회귀 23 + 신규 16: 가입·중복·기업등록·OWNER·초대수락/만료/취소/
  이메일 불일치·ADMIN 상승 차단·교차기업 격리·접근해제·미소속 쓰기 차단·
  비밀번호 변경/재설정·health/db·소속검증)
- 프론트엔드 vite build 통과 (C: 작업공간에서 검증)
- 운영 안전장치 검증: prod+mysql → 데모 차단 / prod+URL 없음 → 시작 거부

### 미완료·외부 설정 대기
- TiDB 실제 접속 검증 — 접속 정보 필요 (DATABASE_URL, DB_SSL_CA)
- 이메일 발송 모듈 — 초대/재설정 토큰 현재 응답 반환 방식
- TiDB 타겟 마이그레이션 실환경 적용
- 프론트엔드 로컬 실행 — E: 드라이브 공간 확보 후 node_modules 설치 필요

---

## 복구·다중 PC 환경 구축 (전환 A 이후 점검 작업)

- E: 드라이브 용량 부족(0바이트)으로 C:에서 수행했던 작업물과 USB 원본을 전수 비교
- `diff -r` 결과 C:\dayribbon-build 소스 = USB 소스 완전 동일 → 누락 소스 없음
- git 이력 2커밋(bfa3b78, 7c77401) 및 전환 A 산출물 전체 USB 보존 확인
- C:에만 있던 인증 정보·중요 파일 없음 확인
- `.gitignore`에 `.env`·`*.pem`·`*.key`·`secrets/` 추가 (인증 정보는 USB 보관·Git 미포함)
- 개발용 `.env`를 프로젝트 루트에 생성 — 실제 키 확보 시 여기에만 기록
- 다중 PC 규칙 확정: USB=소스·git·문서·인증파일, 각 PC=venv·node_modules·빌드 산출물
- 재검증: pytest 39/39 통과, vite build 통과, uvicorn 실기동 + 회원가입/로그인/health-db 실API 확인, vite dev 서빙 + /api 프록시 확인
- 주의: 이 PC의 venv는 `C:\venvs\dayribbon`, 프론트 빌드 작업공간은 `C:\dayribbon-build` (node_modules junction). 다른 PC에서는 각자 `python -m venv` + `npm install` 수행

---

## 정식 전환 단계 B — 실제 데이터 수집 (완료)

### 환경 보완 (전환 B 사전 작업)
- `scripts/sync-local.ps1`/`sync-local.sh`: USB→PC 로컬 작업공간 미러링 (robocopy/rsync).
  .env·*.pem·*.key·secrets/·.git·node_modules·venv·dist·runtime·data 제외 — 민감정보 로컬 복제 차단
- `scripts/check-secrets.ps1`/`.sh`: 민감정보 Git 추적 검사 (git ls-files 스캔)
- `setup.ps1`/`setup.sh`: 동기화→로컬 venv 생성→pip install→npm install 자동화
- `start.ps1`/`stop.ps1`/`start.sh`/`stop.sh`: 로컬 작업공간(`DAYRIBBON_LOCAL`, 기본 C:\dayribbon-build / ~/dayribbon-local)에서 실행하도록 갱신 — 드라이브 문자 무의존(스크립트 위치 기준)
- `.env` USB 보관·Git 미추적·동기화 제외 확인

### 수집기 실구현 (services/collectors/)
- `base.py`: `get_json`/`get_text` HTTP 헬퍼(httpx, 타임아웃·에러 래핑) + Collector 프로토콜
- `EximFxCollector`: 수출입은행 환율 API 실호출 — USD/JPY(100)/EUR/CNH → USD_KRW 등 시계열. EXIM_API_KEY 필요
- `EcosRateCollector`: 한국은행 ECOS StatisticSearch — 기준금리(722Y001/010100000) 월 시계열. ECOS_API_KEY 필요
- `NewsCollector`(news_stub.py): RSS 피드 수집 — API 키 불필요, NEWS_RSS_URLS 다중 피드, xml.etree 파싱, 제목·요약·링크만 저장(원문 전재 없음)

### 수집 서비스 (services/collection_service.py)
- 기업별 저장: 수집 1회 → 모든 기업에 복제 저장(기존 company_id 조회 모델 유지)
- 중복 차단: MarketSeries (company_id, series_key, month) 유니크 upsert, NewsItem link/제목 dedup
- 뉴스 분류: 키워드 기반 카테고리(환율/금리/공급망/원자재/수출입)·감성·기업 프로필 관련도 점수
- 출처 표기: source 필드 + link, 실수집은 is_demo=False — 감사로그 collection.run 기록

### 연동
- `GET /api/collection/status`, `POST /api/collection/run` (ADMIN+) — routers/collection.py
- 스케줄러: COLLECT_INTERVAL_SEC(기본 6h)마다 활성 수집기 전 기업 수집
- 프론트: Settings "데이터 수집" 탭(수집기 상태·수집 현황·수동 실행), 뉴스 상세에 실수집 배지+원문 링크
- 모델: NewsItem.link 추가, MarketSeries 유니크 제약 — 마이그레이션 9a0e03dfc4e4 (upgrade/downgrade 검증)

### 검증
- pytest 52/52 통과 (신규 13: EXIM/ECOS/RSS 파싱·비활성·upsert·dedup·격리·API 권한)
- 실기동 검증: RSS 뉴스 30건 실수집(is_demo=False, 실제 언론사 출처), 재실행 중복 0건

### 외부 설정 대기
- EXIM_API_KEY — 환율 실수집 (구현 완료·키 대기)
- ECOS_API_KEY — 기준금리 실수집 (구현 완료·키 대기)
- NEWS_API_KEY — 검색 API 뉴스 보강 (RSS로 기본 동작 중)

---

## 정식 전환 단계 B 보완 — 공통 데이터·공급처·스케줄 (완료)

### 공통 외부 데이터 저장 구조 (§2)
- `market_series`·`news_items` 공통 데이터를 `company_id=NULL`로 1회 저장 — 기업 수만큼 복제 금지
- `company_news_scores` 테이블 신설: 기업별 뉴스 관련도·중요도·영향 점수 분리 저장
- `utils.company_or_common()` 헬퍼로 기업+공통 범위 쿼리 통일, 소비자(뉴스/대시보드/금융/분석/보고서) 전부 갱신
- 뉴스 API는 공통 뉴스 + 기업 점수를 outerjoin/coalesce로 병합 — 중요도 점수 테이블에서 조회
- 수집 후 생성된 기업도 기존 공통 뉴스 점수가 채워지도록 `run_collector` 보완

### 수집기별 스케줄·이력 (§5)
- `collector_states`: 수집기별 주기(`interval_sec`)·활성화·`last_run_at`/`last_success_at`/`next_run_at`/`cursor`·`last_error`
- `collection_runs`: 수집 이력 (시작/종료·처리·신규·오류·상태)
- `due_collectors()`/`run_due_collectors()` — 스케줄러가 60초마다 기한 도래 수집기만 실행
- 기업 관리자 수동 실행 제한: 기업당 1시간 1회 (`manual_run_allowed`/`mark_manual_run`, 초과 시 429)
- 운영 게이팅: `IS_PROD` + `ALLOW_UNVERIFIED_SOURCES`로 미검증 공급처(RSS) 운영 기본 비활성
- 실패 시 마지막 정상 데이터 유지 + `stale` 최신성 표시

### 신규 데이터 공급처 (§3) — `services/collectors/global_sources.py`
- `GdeltCollector`: 키 불필요 실구현 (DOC 2.0 artlist, 한국어 경제 뉴스 → 공통 뉴스)
- `FredCollector`: `FRED_API_KEY` — 원/달러·미 금리·WTI → 시계열
- `EiaCollector`: `EIA_API_KEY` — WTI 월 시계열
- `DartCollector`: `DART_API_KEY`+`DART_CORP_CODES` — 공시 → 뉴스 매핑
- 공식 문서 기반 어댑터 + Mock 테스트 검증. 키 없으면 `enabled=False` — 스텁이 아닌 실구현

### 이용 조건 문서화 (§4) — `docs/DATA_LICENSES.md`
- 공급처별 상업적 이용·저장·가공·AI 분석·재배포·출처 표시·호출 제한·공식 URL·검토일 기록
- Google 뉴스 RSS: 조건 미확정 → 운영 기본 비활성 + 명시적 플래그로만 활성화

---

## 정식 전환 단계 C — BI·AI 경영 분석 (완료)

### 기업 내부 데이터 확장 (§8)
- `FinancialMonthly`에 `net_income`·`assets`·`liabilities`·`inventory`·`borrowings`·`current_assets`·`current_liabilities` 추가 — nullable로 "미입력"과 "0" 구분
- 재무 입력 API·스키마·CSV 템플릿·한글 컬럼 별칭 확장, 업로드 미리보기/검증 재사용
- 기업 내부 데이터를 가상 값으로 자동 보완하지 않음 (미입력은 NULL 유지)

### KPI 계산 (§9) — `services/kpi_service.py` + `GET /api/kpi`
- 16개 지표 (매출/영업이익/순이익/이익률/성장률/비용증가율/부채비율/유동비율/제조원가/원자재비/재고회전율/제품수익성/거래처의존도/수출입비중/외화결제비중)
- Decimal 기반, 각 지표 `ok`/`insufficient_data`/`not_computable` 상태 + 계산식·기준일·단위 메타
- 데이터 없으면 0 대체 금지, 분모 0은 not_computable

### 기업 맞춤 위험 평가 (§10·§15) — `services/risk_service.py`
- 8개 위험 카테고리, 수출입 구조(수출 중심/수입 중심)에 따라 환율 변동 해석이 상반되게 적용
- 등급: 정상/관심/주의/위험/심각 + `판단 보류`(데이터 부족) — 산정 기준 `ANALYSIS_MODEL.md` 문서화
- 위험 근거·확인 가능 수치를 결과에 포함

### 실제 LLM 모듈 (§11·§12·§21·§22) — `services/llm_provider.py`
- OpenAI 호환 `chat/completions` 실호출 — 공급처 교체 가능 어댑터
- Pydantic `LlmAnalysisResponse`로 구조화 JSON 검증, 타임아웃·429/5xx 지수 백오프 재시도
- `llm_calls` 기록: 토큰·지연·상태. `LLM_MONTHLY_TOKEN_BUDGET` 초과 시 자동 폴백
- 기업 옵트인(`allow_external_ai`) 없으면 호출 차단 — 미승인 기업 데이터 외부 전송 없음
- 인젝션 가드: 외부 데이터 `untrusted_data` 격리 + 지시형 패턴 제거, 최소 데이터만 전송
- LLM 실패/미설정 시 규칙 기반 폴백 — `engine` 필드로 LLM/규칙 엔진 구분 표시

### 자동 분석 (§18) — `analysis_jobs`
- 트리거: 내부 데이터 업로드·프로필 변경·중요 수집 데이터(신규 시계열/고관련 뉴스)·24h 스케줄
- 데이터 내용 해시 서명 `dedup_key`로 중복 분석 방지 (건수만 비교해 값 변경을 놓치던 문제 수정)
- 작업 상태·실패 이력 저장, 결과는 기존 알림 센터 연동

### 프론트엔드 (§20)
- `pages/Kpi.jsx` 신설: KPI 값 + `insufficient_data` 배지, `/app/kpi` 라우트·네비 추가
- Settings: `allow_external_ai` 옵트인 토글, 신규 수집기 상태 표시
- InternalData: 신규 7개 재무 필드 입력 폼·테이블
- 분석 결과의 LLM/규칙 엔진 구분 표시 유지

### 검증
- pytest **94/94 통과** (USB 소스에서 직접 실행 — `docs/TEST_REPORT.md`)
- 마이그레이션 `8d32133b9658`(공통 데이터·수집 작업)·`e6b6ad5682bd`(재무 확장) upgrade/downgrade/upgrade 검증
- 실기동 확인: `/api/kpi` 16개 지표(미입력은 insufficient_data), 위험 API 관심 27.1(수출 기업), 수집 상태 7개 수집기
- 프론트엔드 vite build 통과

### 발생한 오류·해결 (§31)
- 로컬 dev DB가 create_all 생성으로 alembic 버전 없음 → `alembic stamp 8d32133b9658` 후 `upgrade head` 적용
- `run_collection`이 수집기 상태 행을 생성하지 않아 수동 실행이 차단됨 → `ensure_collector_states` 호출 추가
- 분석 중복 서명이 건수만 비교해 값 변경을 놓침 → 데이터 내용 해시로 서명 변경
- `_data_signature`가 `scalar()`로 리스트를 받아 오류 → `first()` 사용으로 수정
- GDELT 실호출: 200 응답·기사 수신 확인했으나 이후 공급처 레이트리밋(429·타임아웃) — 오류 경로 정상 기록 확인, 저장 경로 재검증 대기

### 외부 설정 대기
- LLM_API_KEY/LLM_BASE_URL/LLM_MODEL — 실제 LLM 호출 (구현·Mock 검증 완료)
- EXIM_API_KEY·ECOS_API_KEY·FRED_API_KEY·EIA_API_KEY·DART_API_KEY+DART_CORP_CODES — 실수집
- DATABASE_URL·DB_SSL_CA — TiDB 실접속 (SQLite 마이그레이션 검증 완료)
- 관세청·KOSIS — 공급처 미구현 (키 발급 후 구현 예정 — `DATA_SOURCES.md`)
- GDELT 저장 경로 실수집 재확인 — 공급처 레이트리밋 해소 후

### 다음 단계
- 단계 D(발송·운영)는 지시 있을 때까지 대기 — 임의 진행하지 않음

---

## Render 배포 (2026-11-26 완료)

- **dayribbon-api** (Docker, free): https://dayribbon-api.onrender.com — `APP_ENV=production`, 헬스체크·DB 연결 실검증 (`{"ok":true,"dialect":"mysql"}`)
- **dayribbon-web** (Static): https://dayribbon-web.onrender.com — `VITE_API_BASE` 빌드 주입
- **DB**: TiDB Cloud Serverless `final-dayribbon` (TLSv1.3, `DB_SSL_REQUIRED=1` 시스템 CA) — `alembic upgrade head`로 스키마 생성, 전용 버전 테이블 `dayribbon_alembic_version`
- 레거시 news_articles 11,245건 이관 완료 (공통 뉴스, is_demo=False, dedup 0건)
- Blueprint: `render.yaml` — 정적 사이트 `plan` 필드 제거로 오류 해결
- IP 허용: TiDB 허용 목록은 현재 0.0.0.0/0 — 보안 강화 시 Render outbound 범위(74.220.48.0/24, 74.220.58.0/24)+개인 IP로 축소 가능
- 주의: 무료 플랜 슬립(첫 요청 ~50초 지연), 운영에서 데모 시드·이벤트 자동 비활성
