# dayribbon 데모 → 정식 프로젝트 전환 분석 보고서

작성일: 2026-11-25
분석 대상: `dayribbon-bi-demo` (독립 데모 프로젝트)
목적: 정식 서비스 전환을 위한 전체 소스코드 분석 및 전환 계획 수립

---

## 1. 현재 프로젝트 구조

```
dayribbon-bi-demo/                      (백엔드 약 2,965 LOC / 프론트엔드 약 2,453 LOC)
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI 앱, CORS, 라이프스팬(테이블 생성·시드·스케줄러)
│   │   ├── config.py          # DATABASE_URL, CORS, 스케줄러 주기 등 환경설정
│   │   ├── database.py        # SQLAlchemy 엔진/세션 (SQLite)
│   │   ├── models.py          # 테이블 17개 (SQLAlchemy ORM)
│   │   ├── schemas.py         # Pydantic 요청 모델
│   │   ├── security.py        # PBKDF2 비밀번호 해시, opaque 토큰
│   │   ├── deps.py            # 인증 의존성, 역할 검증, audit() 헬퍼
│   │   ├── seed.py            # 데모 데이터 생성기 (가상 기업 한빛세미텍)
│   │   ├── utils.py           # month_range, fmt_krw 등
│   │   ├── routers/           # API 라우터 13개 파일
│   │   │   ├── auth.py        # 로그인/로그아웃/me
│   │   │   ├── company.py     # 기업정보 조회/수정, 사용자 목록/권한 변경
│   │   │   ├── dashboard.py   # 통합 대시보드 집계
│   │   │   ├── financial.py   # 월별 재무 CRUD + Excel/CSV 업로드 + 이력
│   │   │   ├── news.py        # 뉴스 목록/상세 (필터·관련성)
│   │   │   ├── finance.py     # 시장 시계열 지표 + 영향 설명(하드코딩)
│   │   │   ├── analysis.py    # 분석 결과 조회/실행/검토
│   │   │   ├── simulation.py  # 위험 영향 시뮬레이션
│   │   │   ├── alerts.py      # 위험 알림 + 알림 + 알림 설정
│   │   │   ├── decisions.py   # 의사결정 + 후속조치
│   │   │   ├── reports.py     # 보고서 생성/조회/PDF
│   │   │   ├── audit.py       # 감사 로그 조회(읽기 전용)
│   │   │   └── demo_events.py # 데모 이벤트 (프로덕션 제외 대상)
│   │   └── services/
│   │       ├── analysis_engine.py  # 규칙 기반 분석/위험감지/파이프라인
│   │       ├── simulation.py       # 시나리오 계산 엔진 (순수 계산)
│   │       └── report_service.py   # 보고서 콘텐츠 빌더 + fpdf2 PDF
│   ├── run.py                 # uvicorn 실행 엔트리
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── api.js             # fetch 래퍼 + 포맷 유틸 (토큰은 localStorage)
│   │   ├── auth.jsx           # AuthProvider/로그인 상태
│   │   ├── main.jsx / App.jsx # 라우팅 (13개 라우트)
│   │   ├── components/
│   │   │   ├── Layout.jsx     # 사이드바 레이아웃 + 미확인 알림 배지
│   │   │   └── ui.jsx         # Card/Badge/Stat/ErrorBoundary 등 공통 컴포넌트
│   │   └── pages/             # 화면 13개 (소개/로그인/앱 11개)
│   ├── vite.config.js         # dev 프록시 /api → localhost:8000
│   └── package.json           # React18 + Tailwind v4 + Recharts2 + RRD6
├── sample-data/               # 업로드 테스트용 CSV
├── docs/DESIGN.md             # 설계 결정 문서
├── setup/start/stop .ps1+.sh  # 설치·실행·종료 스크립트 (포트 자동선택)
├── .env.example / .gitignore / README.md
```

### DB 테이블 목록 (17개)

`companies`, `users`, `auth_tokens`, `financial_monthly`,
`product_monthly`, `customer_monthly`, `material_purchases`,
`market_series`, `news_items`, `analysis_results`, `risk_alerts`,
`decisions`, `follow_ups`, `notifications`, `notification_settings`,
`upload_records`, `reports`, `audit_logs`, `demo_events` (총 18개, demo_events 제외 시 17개)

---

## 2. 전체 기능 구현 현황

| 영역 | 구현 상태 | 비고 |
|---|---|---|
| 서비스 소개/로그인 | ✅ 완료 | 랜딩+데모계정 로그인 |
| 권한(OWNER/ADMIN/MEMBER/VIEWER) | ✅ 백엔드 강제 | VIEWER 쓰기 403 실측 |
| 기업 맞춤 설정 | ✅ 완료 | 프로필 수정 → 분석 기준 반영 |
| 통합 대시보드 | ✅ 완료 | KPI 6종+차트 5종+리스트 |
| 뉴스/산업동향 | ⚠️ 데모 데이터 | 필터·상세·관련성 근거 OK, 실제 수집 없음 |
| 금융/경제 지표 | ⚠️ 데모 데이터 | 9개 시계열, 실제 API 없음 |
| 내부 데이터 관리 | ✅ 핵심 완료 | Excel/CSV 업로드·검증·이력 (미리보기 없음) |
| AI 경영 분석 | ⚠️ 규칙 기반 | 성장/방향성/위험 3영역, 근거·불확실성 명시 |
| 위험 시뮬레이션 | ✅ 완료 | 변수→영향 환산+등급+가정 명시 |
| 자동 분석/모니터링 | ✅ 완료 | 업로드/이벤트/주기 트리거 + threading 스케줄러 |
| 알림 센터 | ✅ 기본 완료 | 위험/뉴스/KPI/메일대기 큐 |
| 의사결정/후속조치 | ✅ 완료 | 결정 이력+분석 상태 연동 |
| 월간 보고서+PDF | ✅ 완료 | 실 데이터 집계+한글 PDF (실측) |
| 감사 로그 | ✅ 완료 | 자동 기록, 수정/삭제 불가 |
| 기업별 데이터 분리 | ✅ 스코핑 | company_id 필터 일관 적용(교차 404 실측) |
| 이메일/카카오 발송 | ❌ 미구현 | "발송 대기" 큐만 |
| 주간 요약 알림 | ❌ 미구현 | 설정 플래그만 존재 |
| "분석 완료" 알림 발행 | ❌ 미구현 | 설정 플래그만 존재 |
| 업로드 데이터 미리보기 | ❌ 미구현 | 바로 저장 방식 |
| 제품/거래처/원자재 데이터 CRUD | ❌ 부분 | financial_monthly만 UI CRUD |
| ERP 연동 | ❌ 미구현 | 지시서상 데모 범위 외 |
| PDF/OCR 업로드 | ❌ 미구현 | 명시적 제외 |
| 테스트 코드 | ❌ 없음 | 수동·API 검증만 수행 |
| 배포 구성(Dockerfile/CI) | ❌ 없음 | 로컬 실행 스크립트만 |

### 실제로 동작하는 기능 (검증 완료)
로그인/권한 분리, 회사·사용자·알림설정 CRUD, 재무 월별 CRUD, Excel/CSV 업로드(컬럼 한글 별칭·결측·중복·형식 검증·upsert), 업로드→자동분석 파이프라인, 대시보드 집계, 뉴스/지표 조회, 규칙기반 분석 3종 생성·검토, 시뮬레이션, 위험알림 생명주기, 알림 읽음 처리, 의사결정/후속조치, 보고서 생성·PDF 다운로드, 감사로그, 데모 이벤트 4종, 멀티테넌트 분리.

### 하드코딩/가상 데이터 목록
- `seed.py`: 가상 기업/사용자/24개월 재무/시계열/뉴스 18건 전부
- `routers/finance.py` `IMPACT_NOTES`: 지표 영향 설명 문구
- `routers/simulation.py` `SEVERITY_DESC`, `demo_events.py` `EVENTS`: 등급 설명/이벤트 정의
- `analysis_engine.py` `SEVERITY_RULES`·`DEMO_DISCLAIMER`: 임계값·면책 문구
- `config.py` 기본 SECRET_KEY (※ `security.py`에서 import만 되고 실제 미사용 — 불필요 코드)
- 프론트엔드 페이지 카피·데모계정 표기

### 실제 API 연동 / 실제 AI 여부
- 외부 API 연동: **전무** (시계열·뉴스 모두 시드 생성)
- 실제 AI/LLM: **미사용** — 규칙 기반 `analysis_engine` (화면에 "데모 분석" 명시)
- 자동 수집: 없음. 자동 "분석"은 구현됨(트리거·스케줄러)

---

## 3. 기능 분류 (A/B/C/D)

### A. 그대로 재사용 가능

| 기능 | 파일 | 재사용 이유 |
|---|---|---|
| 위험 영향 시뮬레이션 엔진 | `services/simulation.py` | 순수 계산+가정 명시, 서비스용 수준 |
| 의사결정/후속조치 API+화면 | `routers/decisions.py`, `Decisions.jsx` | 상태머신·이력·연동 완성도 높음 |
| 감사 로그 구조 | `models.AuditLog`, `deps.audit`, `AuditLog.jsx` | 읽기전용·불변성 충족 |
| 보고서 콘텐츠 빌더 | `services/report_service.build_report_content` | 실데이터 집계 구조 그대로 사용 가능 |
| PDF 생성 | `report_service.render_pdf` | 한글 폰트 처리 해결됨(맑은고딕 등) |
| 업로드 검증/upsert 로직 | `routers/financial.py` | 한글 별칭·결측·중복·형식 검증 실증 |
| 알림/위험알림 생명주기 | `routers/alerts.py` | 상태 전이·중복방지 로직 재사용 |
| 분석 엔진 골격 | `services/analysis_engine.py` | KPI 계산 `compute_kpis`·파이프라인 골격 재사용 |
| 프론트엔드 페이지 골격 | `pages/*` | 화면 구성·흐름 유지 지시 반영 |
| 권한 의존성 구조 | `deps.py` | 백엔드 강제 패턴 그대로 |
| 시드 생성 알고리즘 | `seed.py` | 테스트/스테이징용 데이터 생성기로 유지 |

### B. 일부 수정 후 재사용

| 기능 | 수정 내용 |
|---|---|
| 인증(토큰) | 토큰 해시 저장, 회전/만료 정책, 로그인 실패 잠금·레이트리밋 |
| 대시보드 집계 | KPI 캐시 또는 사전집계 테이블 추가 (데이터 증가 대비) |
| 뉴스 화면 | 실제 수집 뉴스 스키마(URL·중복해시·언어·출처)와 관련성 스코어링 결과로 교체 |
| 금융 지표 화면 | 실제 시세 소스 연동, 지표 목록 동적화(하드코딩 IMPACT_NOTES → DB/설정) |
| 알림 설정 | 실제 발송 채널(email SMTP/provider, 카카오 알림톡 템플릿 ID) 연동 |
| 스케줄러 | threading → APScheduler/Celery+Redis 또는 외부 크론(서버 재시작 내성·작업 이력) |
| `monthly` 업로드 | 미리보기·확정 2단계 플로우 추가(스펙의 미리보기 요구 충족) |
| 컬럼 매핑 | 자동 별칭 + 사용자 확인 UI 추가 |
| 프론트엔드 `api.js` | `VITE_API_BASE` 환경변수화, 재시도/타임아웃/에러 표준화 |
| 프론트 디자인 | Tailwind theme → 디자인 토큰 파일 분리(색상/폰트/간격 중앙관리, 전면 개편 대비) |

### C. 실제 서비스용으로 전환해야 하는 기능

| 기능 | 전환 내용 |
|---|---|
| 데이터베이스 | SQLite → **TiDB (Serverless MySQL 호환)**: `DATABASE_URL`을 mysql+connector로 변경, Alembic 마이그레이션 도입 |
| 뉴스/산업 데이터 | 가상 시드 → **실제 수집 파이프라인** (RSS/NewsAPI/네이버 검색 API 등 이용약관 확인 후) |
| 금융/경제 데이터 | 시드 → **실제 시세 API** (한국은행 ECOS, 한국거래소, 외환시세 API 등 무료 소스) |
| AI 분석 | 규칙 기반 → **LLM 분석 모듈** (OpenAI/Anthropic API 또는 오픈모델). 규칙 엔진은 폴백/검증층으로 유지 |
| 뉴스 관련성 스코어링 | 정적 값 → 기업 프로필 매칭 규칙+LLM 분류 |
| 사용자/기업 온보딩 | 시드 계정 → 회원가입·기업 생성·초대·이메일 인증 플로우 신설 |
| 비밀번호/토큰 | 비밀번호 정책, 토큰 해시저장, httpOnly 쿠키 또는 JWT+refresh 고려 |
| 파일 업로드 | 용량 제한, 실제 파일 타입 검증, 바이러스 스캔(선택), 비동기 처리 |
| 보고서 PDF | 서버리스 한글 폰트(내장 NanumGothic 폰트 파일 포함 필요) |
| 데모 전용 기능 | `demo_events` 라우터·UI 제거 또는 feature flag 격리 |
| 로깅/모니터링 | print → 구조화 로깅 + 오류 알림(Sentry 등 무료티어) |
| HTTPS/보안헤더 | Render TLS + SecurityHeaders + CORS 화이트리스트 |

### D. 신규 개발이 필요한 기능

| 기능 | 내용 |
|---|---|
| 외부 데이터 수집기 | 소스별 어댑터(뉴스/환율/금리/원자재)·스케줄·재시도·중복제거·원천 추적 |
| LLM 분석 모듈 | 프롬프트 템플릿·JSON 스키마 검증·비용 제한·폴백(규칙) |
| 기업 온보딩 | 회원가입/이메일인증/기업생성/사용자초대/권한관리 UI |
| 이메일 발송 | SMTP 또는 SendGrid·Resend 무료티어 연동 |
| 카카오 알림톡 | 비즈메시지 발주(사업자 등록 필요, 유료 저가) 또는 카카오 워크/이메일 대체 |
| 업로드 미리보기/컬럼매핑 UI | 파싱 미리보기→확정 저장 2단계 |
| 주간요약 알림 생성 | 주기 요약 집계+발송 |
| 제품/거래처/원자재 CRUD 화면 | financial_monthly 패턴 확장 |
| ERP 연동 준비 | 별도 ERP 프로젝트와의 데이터 수신 인터페이스(웹훅/API) — 직접 연동은 하지 않음(지시서) |
| 관리자(플랫폼) 콘솔 | 다중기업 운영 관리(선택) |
| 테스트 | pytest(백엔드 API)·Vitest/Playwright(프론트 스모크) |
| 배포 | Dockerfile, GitHub Actions CI, Render blueprint, 시크릿 관리 |

---

## 4. 데이터베이스 전환 계획 (SQLite → TiDB)

TiDB는 MySQL 와이어 프로토콜 호환 → **SQLAlchemy 유지**, 접속 문자열만 변경.

1. `requirements.txt`: `pymysql`(또는 `mysql-connector-python`), `alembic` 추가
2. `config.py`: `DATABASE_URL=mysql+pymysql://user:pass@gateway.tidbcloud.com:4000/dayribbon?ssl_verify_cert=true`
3. **Alembic 도입**: `alembic init` 후 현재 `Base.metadata.create_all` 대신 마이그레이션 생성 — 스키마 변경 이력 관리(정식 서비스 필수)
4. 호환성 점검 항목:
   - `Text`/`JSON` 컬럼: TiDB 지원 OK
   - `String` 길이: 유니크 인덱스(`users.email`) 포함 → TiDB OK
   - `Boolean` → TiDB는 TINYINT로 매핑됨(SQLAlchemy가 처리)
   - `onupdate` 서버 트리거 아님(앱 레벨) → OK
   - SQLite 전용 `check_same_thread` 제거 → `database.py` 분기 처리(이미 조건부)
5. 데이터 이관: 시드는 데모 전용이므로 운영 DB엔 온보딩용 빈 스키마만 적용
6. `company_id` 인덱스는 이미 존재 → 테넌트 분리 쿼리 성능 유지

---

## 5. 실제 데이터 수집 연동 계획

| 데이터 | 후보 소스(무료 우선) | 비고 |
|---|---|---|
| 원/달러 환율·금리 | 한국은행 ECOS API | 무료, 회원가입으로 키 발급 |
| 코스피·종목지수 | 한국거래소(KRX) 공공데이터, 네이버/다음 비공식(이용약관 주의) | 공공데이터포털 우선 |
| 나스닥·해외지수·유가·구리 | Stooq(CSV 무료), Yahoo Finance 비공식(약관 위험), FRED(미 금리/지표) | FRED 무료 API 추천 |
| 원자재(웨이퍼 등) | 공공 시세 부재 → 뉴스·지표 프록시로 대체 | 실시세는 유료 |
| 뉴스 | 네이버 검색 API(일 2.5만건 무료), RSS 피드(전자신문 등), NewsAPI(개발 무료·배포 유료) | RSS+네이버 조합 추천 |
| 수출입/무역통계 | 관세청 UNIPASS 공공데이터 | 선택 |

**수집 아키텍처(신규)**: `providers/` 어댑터 패턴 — `fetch()→normalize()→dedupe→save`.
이용약관·저작권: 뉴스는 제목+요약+링크 중심 저장, 전문 복제 지양. 금융 데이터 소스별 재배포 조건 확인 필수.

---

## 6. AI 분석 전환 계획

1. **인터페이스 유지**: `compute_kpis`, `run_analyses`, `detect_risks` 시그니처 유지 → LLM 엔진이 동일 스키마의 `AnalysisResult`를 생성
2. **하이브리드 권장**: 규칙 기반(정량 계산·임계치)은 그대로 유지해 정량 정확성을 보장하고, LLM은 **해석·요약·제안** 문단 생성에 사용 → 할루시네이션 리스크 축소
3. **가드레일**: 프롬프트에 "수치는 제공된 KPI만 인용, 미래 확정 예측 금지" 명시; 출력 JSON 스키마 검증(Pydantic) 후 저장; 실패 시 규칙 엔진 폴백
4. **비용**: 분석 실행당 프롬프트 ~2-4k 토큰. 중소기업 월간 수십 회 → 월 수원 수준(모델에 따라 무료~수 달러). 무료 우선이면 로컬 모델(Ollama) 옵션도 검토
5. **투명성 유지**: `engine` 필드로 규칙/LLM 구분 표기(데모의 면책 설계 계승)

---

## 7. 보안 및 권한 개선 사항

현재 데모 기준 발견 사항과 정식 적용 조치:

| 항목 | 현 상태 | 조치 |
|---|---|---|
| 토큰 저장 | DB 평문 | 해시(SHA-256) 저장 + 만료/회전 |
| 비밀번호 정책 | 없음(데모계정 공통) | 최소 길이·복잡성·변경 주기 |
| 로그인 보호 | 없음 | 실패 잠금, 레이트리밋(slowapi) |
| 인증 전달 | localStorage Bearer | XSS 경로 축소: httpOnly+SameSite 쿠키 권장 (또는 CSRF 대비 현 방식 유지+정책 문서화) |
| SECRET_KEY | 미사용(불필요 코드) | 제거 또는 JWT 도입 시 실사용 |
| CORS | localhost만 허용 | 프로덕션 도메인 화이트리스트 |
| HTTPS | 없음 | Render 기본 TLS 적용 + 보안 헤더 |
| 업로드 | 확장자 검사만 | 용량/타입/내용 검증, 비동기 큐 |
| 감사로그 무결성 | DB 행 기록 | 이전행 해시 체인(선택) 또는 별도 저장소 |
| 개인정보 | 이름/이메일만 | 최소수집·암호화·삭제 요청 처리(PIPA) |
| 기업정보 수정 권한 | MEMBER 허용 | ADMIN 이상으로 상향 검토 |
| 에러 노출 | FastAPI detail 그대로 | 표준 에러 포맷·내부정보 비노출 |
| 의존성 | 핀 없음(최소버전만) | 정식은 버전 잠금+취약점 스캔(pip-audit, Dependabot) |

---

## 8. 2인 개발 추천 작업 순서

개발자 A(백엔드/데이터)와 B(백엔드+프론트) 역할 분담 기준:

**Phase 1 — 기반 전환 (1~2주)**
1. 저장소 생성·CI·환경분리 (dev/stage/prod)
2. TiDB 프로젝트 생성 + Alembic + 스키마 마이그레이션
3. 배포 파이프라인(Render blueprint·시크릿)
4. 온보딩(회원가입·기업생성·초대·이메일인증)

**Phase 2 — 데이터 수집 (2~3주)**
5. 수집기 골격(어댑터/스케줄/중복제거) + 환율·금리·지수(ECOS/FRED) — A
6. 뉴스 수집(네이버/RSS)+카테고리 분류+관련성 스코어링 규칙 — A
7. 지표/뉴스 화면을 실데이터로 전환 — B

**Phase 3 — 분석·알림 실전화 (2~3주)**
8. LLM 분석 모듈(스키마검증+폴백)+규칙엔진 공존 — A
9. 위험 감지 실데이터 임계값 검증·조정 — A
10. 이메일 발송(Resend/SMTP)+카카오 대체안 확정·구현 — B
11. 업로드 미리보기/컬럼매핑 UI, 제품·거래처·원자재 CRUD 확장 — B

**Phase 4 — 운영 완성 (1~2주)**
12. 주간요약·분석완료 알림, 알림 템플릿
13. 보안 개선(토큰 해시·레이트리밋·정책)·감사로그 무결성
14. 테스트(pytest·Playwright 스모크)·관측(Sentry·로그)
15. ERP 수신 인터페이스 명세(직접 연동 X, 계약만 정의)

**Phase 5 — UI/UX 고도화 (별도 후속)**
- 디자인 토큰화 후 전면 개편(이번 범위 아님)

---

## 9. 예상 개발 기간

- **MVP(실데이터 수집+실분석+발송)**: 약 **7~9주** (2인, 파트타임 가정 시 12주+)
- Phase 5 UI/UX 고도화는 별도 일정
- 불확실성: 외부 API 승인 속도(카카오 비즈메시지는 사업자등록·승인 필요)가 일정에 영향

---

## 10. 필요한 API 키 및 외부 서비스

| 서비스 | 용도 | 비용 | 발급 조건 |
|---|---|---|---|
| TiDB Serverless | 운영 DB | 무료(월 25GB·한도 내) | 계정만 |
| 한국은행 ECOS | 환율·금리·지표 | 무료 | 가입 후 인증키 |
| FRED | 미 금리·해외 지표 | 무료 | 계정만 |
| 네이버 검색 API | 뉴스 수집 | 무료(2.5만건/일) | 개발자 등록 |
| RSS | 산업지 뉴스 | 무료 | 없음 |
| LLM API | 분석 생성 | 무료티어(Gemini 등) 또는 월 수~수십달러 | 키 발급 |
| Resend/SendGrid | 이메일 발송 | 무료(일/월 한도) | 계정+도메인 인증 |
| 카카오 알림톡 | 카톡 알림 | 건당 유료(소액) | 사업자등록·채널·템플릿 승인 |
| Render | 호스팅 | 무료(웹+정적) 또는 월 $7~ | 계정 |
| Sentry | 오류 모니터링 | 무료(5k/월) | 계정만 |
| 도메인 | 서비스 URL | 연 ~1.5만원 | 선택 |

---

## 11. 예상 운영 비용 (무료 우선 시나리오)

| 항목 | 무료 구성 | 월 비용 |
|---|---|---|
| DB | TiDB Serverless 무료티어 | ₩0 |
| 호스팅 | Render 무료 웹서비스(스핀다운 있음) | ₩0~9,000 |
| 뉴스/금융 API | 네이버+ECOS+FRED+RSS | ₩0 |
| 이메일 | Resend 무료(100통/일) | ₩0 |
| AI 분석 | Gemini 무료티어 또는 월간 토큰 | ₩0~30,000 |
| 카카오 | (선택) 알림톡 발송 건당 요금 | 건당 ~10~15원 |
| 도메인 | 연비용 환산 | 월 ~1,500 |
| **합계** | | **월 ₩0~5만원 수준** |

※ 무료티어 제약: Render 무료는 유휴 시 스핀다운(콜드스타트 수십초), 네이버 API는 일 한도, 카카오는 유료 채널. 트래픽 증가 시 Render 유료 플랜/DB 상향 필요.

---

## 12. 발견한 오류 및 기술적 문제

| # | 항목 | 심각도 | 조치 |
|---|---|---|---|
| 1 | `security.py`가 `SECRET_KEY`를 import하지만 미사용(불필요 하드코딩 secret 존재) | 낮음 | 제거 또는 JWT 전환 시 실사용 |
| 2 | 테스트 코드 전무 — 회귀 위험(실제로 `fmtDate` import 누락으로 대시보드 백화현상 발생 후 수정된 이력 있음) | 높음 | pytest+프론트 스모크 테스트 필수 |
| 3 | 로그인 레이트리밋 없음 | 중간 | slowapi 또는 게이트웨이 제한 |
| 4 | 업로드 파일 용량·타입 미제한, 요청 스레드에서 pandas 파싱 | 중간 | 사이즈 제한+비동기 |
| 5 | 스케줄러가 인메모리 스레드 — 다중 워커 시 중복 실행·재시작 시 상태 유실 | 중간 | APScheduler+잡스토어 또는 외부 크론 |
| 6 | 감사로그가 일반 DB와 동일 저장소(무결성) | 낮음 | 해시체인 또는 별도 스토리지 선택 |
| 7 | "분석 완료"·"주간 요약" 알림이 설정에만 존재하고 발행 로직 없음 | 낮음 | 발행 로직 구현 |
| 8 | 업로드 미리보기 없이 즉시 저장(지시서 미리보기 요구와 갭) | 중간 | 2단계 플로우 |
| 9 | 제품/거래처/원자재 데이터는 업로드만 되고 UI 수정/삭제 불가 | 중간 | CRUD 확장 |
| 10 | 기업정보 수정이 MEMBER도 허용 — 조직 정책상 ADMIN 권장 | 낮음 | 권한 상향 검토 |
| 11 | 프론트 `api.js`가 `/api` 상대경로만 지원 → 배포 시 프록시/도메인 분리 필요 | 중간 | `VITE_API_BASE` 환경변수 |
| 12 | 데모 이벤트 라우터가 프로덕션 노출 시 실데이터 오염 가능 | 중간 | feature flag로 제거/격리 |
| 13 | `company_id`가 nullable인 `market_series`/`news_items` — 공통데이터용 의도이나 검증 불명확 | 낮음 | 테넌트 분리 규칙 명시 |
| 14 | 에러 경계(ErrorBoundary)는 추가했으나 404/빈 페이지 대비 라우트 fallback 검증 필요 | 낮음 | 확인됨(동작 중) |

---

## 13. 배포 가능 여부 평가

| 항목 | 평가 |
|---|---|
| 코드 배포 가능성 | 기술적으로 Render에 즉시 배포 가능(uvicorn+정적빌드) |
| 실제 서비스 준비도 | ❌ — 실데이터 수집·실AI·온보딩·보안·법적검토 필요 |
| 데모→정식 전환 난이도 | **중간-낮음**: 라우터/모델/서비스 분리가 잘 되어 있어 점진 전환 가능 |

---

## 14. 정식 프로젝트 전환 가능 여부: **가능**

- 재사용률: 코드 골격의 약 **60~70%**가 A/B에 해당 — 재작성 불필요
- 핵심 전환 과제 3개: ① 실데이터 수집 파이프라인 ② LLM 분석 모듈(규칙 폴백 유지) ③ 온보딩+보안 하드닝
- 리스크: 카카오 알림톡 승인 지연(대체 이메일로 우선 출시), 무료 금융API의 원자재 시세 커버 한계
- 권고: **Phase 1~2(기반+수집)부터 착수**하되, 규칙기반 분석을 MVP로 출시하고 LLM은 점진 도입 — 초기 품질 안정 확보에 유리
