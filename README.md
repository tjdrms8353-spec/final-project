# dayribbon — 중소기업 맞춤형 BI 시스템

AI 기반 중소기업형 맞춤형 BI(경영 인텔리전스) 시스템의 **정식 서비스 프로젝트**입니다.
재무 데이터 업로드 + 외부 시장 데이터(환율·금리·뉴스) 수집 → 분석·위험 감지·
의사결정·보고서까지 제공합니다.

## 폴더가 2개인 이유

USB의 `dayribbon/` 폴더 아래에는 성격이 다른 두 프로젝트가 있습니다.

| 폴더 | 역할 |
|---|---|
| `dayribbon-bi-demo/` | **원본 데모** — 처음 개발한 시연용 코드. 데모 계정·가상 데이터 포함. 보존용이며 수정하지 않음 |
| `dayribbon/` | **정식 서비스 프로젝트 (이 저장소)** — 데모를 기반으로 회원가입·기업별 격리·실데이터 수집 등 정식 전환을 진행 중인 독립 git 저장소 |

데모를 덮어쓰지 않고 별도 폴더에서 전환하는 이유: ① 시연 가능한 데모를 유지하기 위해
② 데모용 가상 데이터와 실서비스 데이터의 혼합을 막기 위해.

문서: `작업일지.md`(기능별 목적·방식·사용법), `docs/PRODUCTION_PLAN_A.md`(전환 단계),
`docs/dayribbon_project_plan.pdf`(기획서)

## 기술 스택

- **Frontend**: React 18 + Vite + Tailwind CSS v4 + Recharts + React Router
- **Backend**: Python FastAPI + SQLAlchemy + Pydantic + SQLite
- **데이터 처리**: Pandas (Excel/CSV 업로드), fpdf2 (한글 PDF 보고서)

## 실행 방법 (다중 PC 구조)

소스는 USB에 보관하고, 가상환경·node_modules 등은 **각 PC 로컬 작업공간**에 설치됩니다.

```powershell
# 1) 최초 1회 — USB 소스를 로컬 작업공간(C:\dayribbon-build)으로 동기화 후
#    가상환경·node_modules 설치
.\setup.ps1

# 2) 실행 (로컬 작업공간에서 백엔드+프론트엔드 동시)
.\start.ps1

# 3) USB의 최신 소스를 로컬에 반영하고 싶을 때
.\scripts\sync-local.ps1
```

- 로컬 작업공간 위치: `DAYRIBBON_LOCAL` 환경변수 (기본 `C:\dayribbon-build`, Linux/macOS `~/dayribbon-local`)
- `.env`·API 키는 USB에만 보관되고 로컬로 복제되지 않습니다 (`scripts\check-secrets.ps1`로 Git 추적 여부 검사 가능)
- 모든 스크립트는 자기 위치 기준 경로 — USB 드라이브 문자(E:/F:)가 바뀌어도 동작

Linux/macOS:

```bash
chmod +x setup.sh start.sh stop.sh scripts/*.sh
./setup.sh
./start.sh
```

포트가 사용 중이면 자동으로 다음 사용 가능한 포트를 선택합니다.
실행 후 출력되는 주소로 접속하세요.

## 스크립트 설명

`setup`/`start`/`stop`이 각각 `.ps1`(Windows PowerShell용)과 `.sh`(Linux/macOS bash용)
두 개씩 있는 이유는 **같은 기능을 운영체제별로 제공**하기 때문입니다.

| 파일 | 하는 일 |
|---|---|
| `setup` | 최초 1회 설치 — USB 소스를 로컬 작업공간으로 동기화 → Python 가상환경 생성 + 라이브러리 설치 → 프론트엔드 `npm install` |
| `start` | 실행 — 로컬 작업공간에서 백엔드(FastAPI)와 프론트엔드(Vite)를 함께 실행. 사용 중인 포트를 피해 자동 선택 후 접속 주소 출력 |
| `stop` | 종료 — `start`가 기록해둔 프로세스 ID를 읽어 두 서버를 종료 |

Windows면 `.ps1`, Mac/Linux면 `.sh`를 실행하면 됩니다.

보조 스크립트(`scripts/`):

| 파일 | 하는 일 |
|---|---|
| `sync-local` | USB 소스 → 로컬 작업공간 미러링 (`.env`·인증서는 복제 제외) |
| `check-secrets` | `.env`·인증서·키 파일이 Git에 추적되고 있는지 검사 |

## 접속 주소 (기본값)

| 항목 | 주소 |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

## 데모 로그인

비밀번호는 모두 `demo1234` 입니다.

| 권한 | 이메일 | 설명 |
|---|---|---|
| OWNER | owner@dayribbon.demo | 기업 대표 — 전체 권한 |
| ADMIN | admin@dayribbon.demo | 관리자 — 분석 검토·의사결정 권한 |
| MEMBER | member@dayribbon.demo | 실무 — 데이터 등록·수정 권한 |
| VIEWER | viewer@dayribbon.demo | 읽기 전용 — 외부 감사 역할 (수정 API 403 차단) |

## 데모 데이터

- 가상 기업: **(데모) 한빛세미텍** — 반도체 부품 제조업
- 최근 24개월 매출/영업이익/비용, 제품별·거래처별 실적, 원자재 구매
- 환율·금리·주가지수·원자재가 24개월 시계열
- 산업 뉴스 18건 (모두 가상)
- 첫 실행 시 자동 시드 (`SEED_DEMO=1`). DB는 `backend/data/dayribbon.db`

## 데모 이벤트 (알림 센터 메뉴)

테스트용 시장 변동 재현 버튼입니다. 실제 금융 데이터가 아니며,
실행 시 데이터 등록 → 분석 → 위험 판단 → 알림 → 대시보드 갱신이 실제로 수행됩니다.

## 핵심 기능

- 회원가입·온보딩 (기업 등록 → OWNER 부여 → 빈 상태로 시작)
- 기업 워크스페이스 (초대·권한 OWNER/ADMIN/MEMBER/VIEWER·기업별 데이터 격리)
- 통합 경영 대시보드 (KPI·차트·위험 현황)
- 실데이터 수집 — RSS 뉴스(키 불필요)·수출입은행 환율·한국은행 금리(키 필요), 6시간 자동 수집·중복 차단·출처 표기
- 뉴스/산업 동향 (기업 관련성 점수 기반 선별, 실수집 기사는 원문 링크)
- 금융·경제 지표 (기업 영향 설명 포함)
- 내부 데이터 관리 (Excel/CSV 업로드 미리보기 2단계, 검증, 이력)
- AI 경영 분석 (LLM 연동 인터페이스 + 규칙 기반 폴백, 근거·불확실성 명시)
- 위험 영향 시뮬레이션 (환율/금리/원자재/매출 변동)
- 자동 분석·모니터링 (업로드·이벤트·주기적 위험 감지·주간 요약)
- 알림 센터 (위험/뉴스/KPI/분석 완료 — 알림 설정 연동)
- 의사결정·후속 조치 관리 (사람이 최종 결정)
- 월간 경영 보고서 + PDF 다운로드 (한글 지원)
- 감사 추적 로그 (읽기 전용)
- 역할 기반 권한 (백엔드 API 레벨 강제)

## 프로젝트 구조

```
dayribbon/
├── frontend/          # React + Vite SPA
│   └── src/pages/     # 화면별 페이지 (Signup/Onboarding 포함)
├── backend/
│   ├── app/
│   │   ├── routers/   # API 라우터 (기능별 분리, collection 포함)
│   │   ├── services/  # 분석엔진/시뮬레이션/보고서/llm_provider
│   │   │   └── collectors/  # EXIM 환율·ECOS 금리·RSS 뉴스 수집기
│   │   ├── models.py  # SQLAlchemy 모델 (22테이블, TiDB 전환 대비)
│   │   └── seed.py    # 데모 데이터 생성 (SEED_DEMO=1일 때만)
│   ├── alembic/       # DB 마이그레이션
│   ├── tests/         # pytest (52개)
│   └── run.py
├── scripts/           # sync-local(동기화)·check-secrets(민감정보 검사)
├── sample-data/       # 업로드 테스트용 CSV
├── docs/              # 설계·전환 계획·기획서 PDF
├── 작업일지.md         # 기능별 목적·방식·사용법 기록
├── setup.ps1 / start.ps1 / stop.ps1
├── setup.sh / start.sh / stop.sh
└── .env.example
```

## 환경 변수

`.env.example` 참고. 주요 항목: `DATABASE_URL`, `SECRET_KEY`, `SEED_DEMO`,
`AUTO_ANALYSIS_INTERVAL_SEC`, `CORS_ORIGINS`, `VITE_BACKEND_URL`.

## 현재 상태·제한 사항

- LLM 분석은 `LLM_API_KEY`/`LLM_BASE_URL` 설정 시 활성 — 미설정·실패 시 규칙 기반 엔진으로 자동 폴백 (화면에 근거 명시)
- 뉴스는 RSS로 실제 수집됩니다(키 불필요). 환율·금리는 `EXIM_API_KEY`/`ECOS_API_KEY` 설정 시 실수집, 미설정 시 해당 수집기 비활성
- TiDB/MySQL 연결 모듈·마이그레이션 완비 — 실제 접속 정보(`DATABASE_URL`·`DB_SSL_CA`)는 외부 설정 대기
- 이메일/카카오 알림은 발송 모듈 미연동 (토큰 구조만 구현)
- PDF 재무제표 OCR 및 ERP 연동은 미구현입니다
- 데모 계정·데모 데이터는 `SEED_DEMO=1`(dev 기본)일 때만 생성, production에서는 자동 차단
