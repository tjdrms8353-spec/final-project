# Final Project

<!-- 고정: "실행 방법" 섹션은 항상 이 파일의 맨 위에 둔다. 작업 기록은 아래 "작업 기록"에 날짜순으로 추가한다. (AGENTS.md 규칙) -->

## 실행 방법 (고정)

작업 폴더: VS Code에서 `E:\송성근(심화)\finalProject\Finalproject-main`을 엽니다. 바깥 `finalProject\` 폴더의 같은 이름 파일은 개발 기준이 아닙니다. 아래 명령은 모두 이 폴더(프로젝트 루트)에서 PowerShell로 실행합니다.

### 1. 최초 준비 (한 번만)

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements-dev.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }                    # TiDB 접속 정보 입력
if (-not (Test-Path frontend/.env)) { Copy-Item frontend/.env.example frontend/.env }
cd frontend; npm.cmd install; cd ..
.\.venv\Scripts\python -m alembic -c backend/alembic.ini upgrade head        # DB 테이블 생성·갱신
```

Airflow(WSL Ubuntu) 최초 설치 방법은 아래 [Airflow 예약 수집](#airflow-예약-수집) 참고. 이 PC에는 설치되어 있습니다.

### 2. 매일 실행

**한 번에 실행: 프로젝트 폴더의 `start-dev.bat` 더블클릭** → 백엔드·프론트엔드 창 2개가 열리고 약 6초 뒤 브라우저가 열립니다. 종료는 두 창을 닫습니다. 뉴스 자동 수집(Airflow)은 Windows 로그인 시 자동으로 실행됩니다.

| 순서 | 대상 | 방법 | 확인 주소 |
| --- | --- | --- | --- |
| ① | 뉴스 자동 수집 (Airflow) | Windows 로그인 시 **자동 실행**. 수동: `Win+R` → `shell:startup` → `start-final-airflow.vbs` 더블클릭 (화면 안 뜸이 정상) | http://localhost:8080 |
| ② | 백엔드 | `start-dev.bat`에 포함. 따로 실행: `.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8001` | http://127.0.0.1:8001/docs |
| ③ | 프론트엔드 | `start-dev.bat`에 포함. 따로 실행: `cd frontend; npm.cmd run dev -- --host localhost --port 5175 --strictPort` | http://localhost:5175 |

- E: USB가 꽂혀 있어야 수집됩니다. 5173·5174 포트는 ONFIT 서버용이라 사용하지 않습니다.
- PowerShell에서 `npm`이 차단되면 `npm.cmd`를 사용합니다. Docker 백엔드: `docker compose up --build`.
- Airflow 중지: `wsl -d Ubuntu --exec pkill -f "bin/airflow standalone"`
- Airflow 웹 로그인: 아이디 `admin`, 비밀번호는 `wsl -d Ubuntu --exec cat /home/pc06-00/airflow/simple_auth_manager_passwords.json.generated` 결과의 따옴표 안 값

### 3. 동작 확인

| 확인 항목 | 방법 |
| --- | --- |
| 백엔드 상태 | http://127.0.0.1:8001/health → `{"status":"ok"}` |
| 저장된 뉴스 | http://127.0.0.1:8001/api/news?limit=5 |
| 출처별 수집 공백 | http://127.0.0.1:8001/api/news/coverage?hours=24 (`gaps`가 비어 있으면 공백 없음) |
| Airflow 수집 상태 | WSL: `wsl -d Ubuntu --exec curl -s http://localhost:8080/api/v2/monitor/health` |
| 뉴스 화면 | http://localhost:5175 → 뉴스·SNS 탭 |
| BBC 번역 | 화면의 **출처 이름**에 `BBC News`를 정확히 입력하고 **검색** 클릭(`bbc`만 입력하면 0건) → 한국어 제목과 "기계 번역 · 원문" 표시. 상태 확인(dry-run, 외부 요청 없음): `$env:PYTHONPATH='backend;.'; .\.venv\Scripts\python -m pipelines.jobs.translate_news`. 수동 `--execute`는 DeepL 요청·DB 저장을 수행하므로 별도 확인 후 실행 |

### 4. 테스트

```powershell
.\.venv\Scripts\python -m pytest -c backend/pytest.ini backend/tests       # 백엔드
.\.venv\Scripts\python -m pytest -c pipelines/pytest.ini pipelines/tests   # 수집 파이프라인
cd frontend; npm.cmd run typecheck; npm.cmd run build; cd ..              # 프론트엔드
```

---

## 작업 기록 (날짜순)

> 근거 표시: (Git) 커밋, (문서) 기존 기록, (파일) 파일 수정 시각, (검증) 실행·테스트로 확인. 개발 순서와 진행 현황은 `docs/DEVELOPMENT_PLAN.md`, `docs/PROGRESS.md`를 함께 봅니다.

### 2026-11-16
- GDELT 뉴스 수집기(`collectors/gdelt.py`, `pipelines/jobs/collect_gdelt.py`) 작성. 기본 dry run, 저장 없음 (파일)

### 2026-11-17
- 팀 프로젝트 초기 구성: frontend(React+Vite)·backend(FastAPI)·pipelines·migrations 폴더, 기능별 라우터(`/api/news`, `/api/finance`, `/api/erp`)와 status API, `/health` (Git)
- Google AI Studio 데모 화면 통합, 기존 HTML 화면을 `frontend/public/legacy`로 이동 (Git)
- Vite 개발 캐시를 Git 제외 대상에 추가 (Git)

### 2026-11-18 (Codex)
- Python 3.12 `.venv` 준비, 백엔드 `/health`·`/docs`·`/api/news/sample` 응답 확인 (문서)
- 뉴스 샘플 API·전처리 복구, TiDB TLS 연결·Alembic 설정 (문서·파일)
- RSS 수집기(BBC Technology, SBS 속보) 작성, 소량 실제 수집 5건 검증 통과 (문서)
- DB 마이그레이션 01~04: 뉴스 테이블, 수집 이력, 시도 횟수, 실행 주체 (파일)
- 수집 안정화: 요청 제한 대기(429·Retry-After), 일시 오류 재시도, 동시 실행 잠금, 중단 작업 처리 (파일)
- 저장 뉴스 조회 API(`GET /api/news`, `/api/news/{article_id}`)와 React 목록·검색·상세 화면 (파일)
- 로컬 주기 수집 스케줄러 `schedule_rss` 작성 (파일)

### 2026-11-19 (Devin 인수)
- 프로젝트 분석, 인수인계 문서 작성: `docs/DEVELOPMENT_PLAN.md`, `docs/PROGRESS.md`, `docs/HANDOFF.md`, `AGENTS.md` 공통 규칙 (검증)
- 로컬 스케줄러 실환경 검증: BBC·SBS 30분 간격 2회 성공, 중복 실행 방지 확인 (검증)
- WSL Ubuntu 설치, Airflow 3.4.0 설치, 출처별 DAG 작성 → 예약 실행 2회 성공 → **2단계 주기적 수집 완료** (검증)
- 피드당 수집 건수 5→100건: SBS에서 놓치던 기사 80건 확보 (검증)
- 개발 순서 확정(사용자 결정): 4단계 해외 뉴스 자동 번역 추가, SNS 수집을 TOP 10 앞으로, 배포는 최종 단계(무료·개인별)
- 3단계 수집 범위 확대: 한국 출처 9곳 추가(연합뉴스·연합뉴스TV·동아·한경·뉴시스·조선·오마이·경향·한겨레), ISO 8601·`dc:date` 날짜 지원, 한겨레 수집 시각 저장, 수집기 User-Agent로 한국경제 403 해결, 간격 한국 5분·BBC 15분 → 1회차 신규 539건 (검증)
- MBC·KBS·YTN(RSS 폐지)·JTBC(갱신 중단)·매일경제(403)·파이낸셜뉴스(갱신 지연)는 제외
- 분야 저장·수집 공백 기록 구현, 마이그레이션 05 적용(`news_article_sections`, `window_start_at`) (검증)

### 2026-11-23 (Devin)
- 11-19~11-23 수집 중단 원인 확인: 작업 도구 터미널에서 띄운 Airflow가 도구 종료와 함께 꺼짐 → Windows 시작프로그램 `start-final-airflow.vbs`로 로그인 시 자동 실행 (검증)
- 분야 피드 41개(30분 간격) 포함 Airflow DAG 52개 가동, 동시 실행 8개 제한 (검증)
- 재가동 검증: 86회 성공, 신규 기사 873건, 분야 2,754건. 중단 기간을 `/api/news/coverage`가 missed로 검출 (검증)
- 저장 실패 1건(연합뉴스, 동시 실행 시각) 원인 확인을 위해 DB 오류 번호 기록 추가 (검증)
- 테스트: backend 94개, pipelines 55개 통과 (검증)
- README 재구성: 실행 방법 고정, 날짜별 작업 기록 추가
- `start-dev.bat` 추가: 백엔드·프론트엔드 한 번에 실행 (검증: `/health` ok, 프록시 경유 `/api/news` 200)
- **3단계 수집 범위 확대 완료** (사용자 확인). 남은 확인: RSS 이용 조건 7곳
- 4단계 해외 뉴스 자동 번역 착수 (사용자 결정: DeepL API, 제목+요약)
- BBC 요약(`description`) 저장, 기존 기사는 빈 요약만 채움 (검증)
- 번역 기능 구현: `translation.py`(DeepL), `pipelines/jobs/translate_news.py`, 마이그레이션 06 `news_translations` 적용, Airflow `news_translate_ko`(15분) 등록, 뉴스 API `title_ko`·`summary_ko`, 화면에 번역 제목·원문 표시 (검증: 당시 테스트 backend 106·pipelines 60, DAG 로드)
- DeepL 키 인식 확인(값 미출력), Airflow 번역 DAG 2회 success. BBC 34건 중 한국어 제목 25건·요약 14건 저장; 미번역 9건은 예약 처리 대기. API 목록·상세에서 원문과 번역 동시 반환 200, 프론트 프록시 200 (검증)
- DeepL 429·5xx 오류에 최대 2회 지수 백오프(1초·2초), 400·456은 재시도하지 않도록 보완. 관련 테스트 backend 36·pipelines 5, Python compileall, 프론트 typecheck·build 통과(번들 크기 경고). 수동 DeepL 요청 없음 (검증)
- UTC 08:35 Airflow 예약 실행 success: BBC 34건 모두 제목 번역, 요약이 있는 21건 모두 요약 번역, 미번역 0건. `source=BBC News`로 API 조회 34건·최신 5건 번역 확인(`bbc`는 정확히 일치하지 않아 0건). 브라우저 화면 직접 확인은 대기 (검증)

---

## 상세 참고

### 역할

| 담당 | 역할 | 기술 |
| --- | --- | --- |
| 프런트엔드 1명 | 전체 화면, 대시보드, API 연결 | React, Tailwind, Recharts |
| 성근 | 뉴스·SNS 수집, AI 문서 분류, TOP 10, ETL | Python, FastAPI, Airflow, Polars, Scikit-learn |
| 종범 | 주식·코인 수집 및 분석 | Python, FastAPI, Pandas, 금융 API |
| 승호 | 영수증 OCR 및 자동 등록 | Python, FastAPI, OCR, Playwright |
| 공동 | DB, API 통합, 테스트, 배포 | TiDB, SQL, GitHub, Render, EC2 |

상세 실행·확인 절차는 [로컬작업.md](로컬작업.md)를 참고하세요.

### 구조와 구현 범위

- frontend/: React 시작점 및 기존 화면(public/legacy)
- backend/app/features/: trends(성근), finance(종범), receipts(승호)
- backend/app/core, db, models, schemas: 공통 설정·DB·모델·스키마
- pipelines/: Airflow DAG, ETL 작업, 테스트(별도 Python 환경)
- models/, data/: 로컬 모델·데이터 저장 위치
- migrations/: Alembic 초기화 및 DB 변경 파일을 추가할 위치
- docs/: planning, design, implementation, deployment
- .github/workflows/: 프런트엔드 빌드 및 Python 구문 검사 CI

백엔드는 `/health`, `/api/health`와 `/api/news/status`, `/api/finance/status`, `/api/erp/status`를 제공합니다. 기존 `/api/v1` 상태 API도 호환됩니다. 뉴스 모듈은 개인 TiDB에 연결해 수집·저장·조회와 Airflow 예약 수집까지 동작합니다(마이그레이션 `20261123_06` 적용). 해외 뉴스 번역은 구현되어 실환경 검증 중이며, 금융·OCR·뉴스 분류·TOP 10·배포는 아직 구현되지 않았습니다.

DB 설정은 루트 `.env`, 프론트 개발 프록시 설정은 `frontend/.env`의 `DEV_API_TARGET`으로 관리합니다. React는 `/api/...` 상대 경로로 호출합니다. 선택 기술은 `backend/requirements-optional/`로 분리했으며 기본 설치에 포함하지 않습니다.

백업의 뉴스 샘플·전처리·GDELT 수집 코드와 관련 테스트를 복구했습니다. `/api/news/sample`은 가상 기사만 반환합니다. `pipelines/jobs/collect_gdelt.py`는 기본 dry run이며 실제 수집에는 명시적인 `--execute`가 필요합니다. 이번 복구에서 외부 수집·DB 접속은 수행하지 않았습니다.

### RSS 수집 (수동 확인용 CLI)

BBC Technology RSS 소량 수집 확인(프로젝트 루트, PowerShell):

```powershell
$env:PYTHONPATH = 'backend;.'
.\.venv\Scripts\python -m pipelines.jobs.collect_rss --limit 5
# 실제 피드 1회 요청. 원문 크롤링·파일 저장·DB 적재 없음.
.\.venv\Scripts\python -m pipelines.jobs.collect_rss --limit 5 --execute
# 개인 TiDB 설정 및 뉴스 테이블 마이그레이션 적용 후에만 사용
.\.venv\Scripts\python -m pipelines.jobs.collect_rss --limit 5 --execute --store
```

RSS 피드 전체 응답은 최대 2 MiB로 제한하고 첫 5개 항목을 검사합니다. 이는 전체 뉴스·실시간 순위 데이터가 아닙니다. 기사 출처와 원문 링크를 유지하며 발행일이 없는 항목은 제외합니다. 2026-11-18 소량 확인에서 5개 항목이 검증을 통과했습니다.

`--store`는 검증 실패 항목이 없는 배치만 하나의 트랜잭션으로 저장합니다. 같은 URL은 최초 저장 내용을 유지합니다. `storage=committed`는 저장 트랜잭션 성공을 뜻하며 새로 추가된 기사 수가 아닙니다. 테이블은 자동 생성하지 않습니다.

`--execute --store` 실행은 `news_collection_runs`에 출처, UTC 시작·종료 시각, 상태, 검증·중복·신규 저장 건수와 오류 코드를 기록합니다. 신규 건수는 `inserted_count`, 기존 URL 건수는 `existing_count`, 한 피드 안의 중복은 `duplicate_count`입니다. 수집 응답을 못 받은 경우 입력 건수는 0이 아닌 NULL입니다. DB 이력을 시작할 수 없으면 외부 요청도 실행하지 않습니다. 강제 종료 시 `running` 기록이 남을 수 있으며, DB 장애로 종료 기록에 실패하면 `history=finalization_failed`를 출력합니다. dry run과 저장 없는 실행은 DB 이력을 남기지 않습니다. DB 저장 오류는 `database_write_<드라이버 오류 번호>`로 기록합니다(메시지·SQL은 기록하지 않음).

저장 수집은 같은 PC·프로젝트·출처에서 동시에 실행할 수 없습니다. 실행 중이면 `collection_busy`로 종료하며 외부 요청을 보내지 않습니다. 프로세스 종료 시 OS가 잠금을 해제하므로 `.cache/collection-locks` 파일을 직접 삭제하지 마세요. 여러 서버 사이의 분산 잠금은 아직 지원하지 않습니다. 다음 저장 수집에서 잠금을 확보하면 같은 PC·프로젝트·출처가 남긴 running 이력을 interrupted로 변경합니다. finished_at은 실제 종료 시간이 아닌 중단 발견 시각입니다. 소유자 정보가 없는 과거 이력과 다른 PC의 이력은 자동 변경하지 않습니다.

```sql
SELECT feed, started_at, finished_at, status, inserted_count, existing_count,
       rejected_count, error_code
FROM news_collection_runs
ORDER BY started_at DESC, run_id DESC
LIMIT 20;
```

한국어 뉴스는 `--feed sbs-latest`로 선택합니다. 예:

```powershell
.\.venv\Scripts\python -m pipelines.jobs.collect_rss --feed sbs-latest --limit 5 --execute --store
```

기본 출처는 `bbc-tech`입니다. 등록 출처(2026-11-19 확인): `sbs-latest`, `yna-all`(연합뉴스), `yonhapnewstv-latest`(연합뉴스TV), `donga-all`, `hankyung-all`, `newsis-sokbo`, `chosun-all`, `ohmynews-all`, `khan-all`(경향), `hani-all`(한겨레)와 분야 피드 41개(`yna-politics`, `hankyung-it` 등). 수집기는 `FinalProjectNewsBot/0.1` User-Agent를 보냅니다(한국경제는 라이브러리 기본 UA를 403으로 차단). 날짜는 RSS `pubDate`(RFC 822 또는 ISO 8601)와 `dc:date`를 읽으며, 기사별 날짜가 없는 한겨레는 처음 수집한 시각을 `observed_at`으로 저장합니다. MBC·KBS·YTN은 공식 RSS가 폐지되어, JTBC는 2024-10 이후 갱신이 멈춰 등록하지 않았습니다. 자동 대체·반복 요청은 하지 않습니다.
[SBS 공식 RSS 안내](https://news.sbs.co.kr/news/rss.do)는 개인의 비상업적 사용만 허용하며 상업적 사용은 사전 문의가 필요하다고 명시합니다(연합뉴스·연합뉴스TV·동아일보도 같음). 현재는 개인 개발 검증용으로 제목·원문 링크·발행일·출처만 수집하고 기사 본문은 크롤링하지 않습니다. 공개 서비스 이용 범위는 별도로 확인해야 합니다.

### 뉴스 조회 API

저장 뉴스 조회: `GET /api/news?limit=20&offset=0&q=AI&source=BBC%20News`.
`q`는 제목 부분 검색, `source`는 출처 일치 필터이며 생략할 수 있습니다.
`total`은 필터 적용 후 페이지 제한 전 개수입니다. 최신순(발행 시각, 없으면 관측 시각)으로 반환합니다.
상세 조회는 목록의 `article_id`를 사용한 `GET /api/news/{article_id}`입니다.
기존 `id`는 수집 출처 식별자이므로 상세 경로에 사용하지 않습니다.
없는 기사는 404, 잘못된 입력은 422, DB 사용 불가는 503입니다.
응답의 `data_source=database`는 저장된 데이터라는 뜻이며 자동 실시간 갱신을 의미하지 않습니다.

수집 공백 조회: `GET /api/news/coverage?hours=24&feed=yna-all` (`hours` 1~720). `missed`는 피드 보관 범위가 직전 수집과 이어지지 않아 기사가 빠졌을 수 있는 구간, `unverified`는 보관 범위 기록이 없고 간격이 1시간을 넘은 구간, `ongoing`은 최근 수집이 멈춘 상태입니다.

분야: 연합·동아·한경·SBS·연합TV 분야 피드 41개(30분 간격)와 오마이·경향 피드 내 분야를 `news_article_sections`에 언론사 원래 이름으로 저장합니다(마이그레이션 `20261119_05`). 분야 이름 통일은 AI 분류 단계에서 합니다.

### 프론트엔드

기존 HTML과 자산은 상대 경로를 유지한 채 frontend/public/legacy로 옮겼습니다. React의 대시보드 페이지는 iframe으로 기존 화면을 표시합니다. React로 완전히 변환된 상태는 아닙니다. 트렌드·금융·문서 AI·영수증 OCR·운영 콘솔은 Google AI Studio의 데모 화면으로 통합했습니다. 뉴스 탭의 "수집된 뉴스" 목록만 실제 DB 데이터입니다. 대시보드는 기존 화면을 유지하며 기존 업로드 화면도 하단 링크에서 이용할 수 있습니다.
기존 프런트엔드 문서는 docs/implementation/legacy-frontend.md에 있습니다.

### 로컬 주기 수집 (Airflow 대체용)

```powershell
$env:PYTHONPATH = 'backend;.'
# 기본은 dry run: 네트워크·DB 작업 없음
.\.venv\Scripts\python -m pipelines.jobs.schedule_rss --feed bbc-tech:1800 --feed sbs-latest:1800
# 출처별 30분 간격, 각 2회 실행 후 종료(첫 수집은 즉시 실행)
.\.venv\Scripts\python -m pipelines.jobs.schedule_rss --feed bbc-tech:1800 --feed sbs-latest:1800 --cycles 2 --execute
```

`--cycles 0 --execute`는 Ctrl+C까지 실행합니다. 터미널·PC가 켜져 있어야 하며 백그라운드 서비스가 아닙니다. 최소 간격은 300초이고 운영 주기는 각 출처 조건에 맞춰 설정합니다. 작업 완료 후 간격을 두며 밀린 수집을 연속 실행하지 않습니다. 재시작 시 일정은 초기화됩니다. 같은 출처 중복 실행은 기존 로컬 잠금으로 차단하며 여러 서버 간 일정 조정은 지원하지 않습니다. **Airflow와 동시에 실행하지 않습니다**(Windows·WSL 잠금이 공유되지 않음).

### Airflow 예약 수집

`pipelines/dags/news_rss_collection.py`가 `pipelines/jobs/airflow_rss.py`의 `SCHEDULES`에 있는 출처별 DAG(`news_rss_<출처>`) 52개를 등록합니다. 한국 전체 피드 10곳은 5분, BBC는 피드 권장값(`<ttl>15</ttl>`)인 15분, 분야 피드 41개는 30분 간격입니다. 실행 사이에 게시된 기사를 놓치지 않도록 매번 피드 항목을 최대 100건까지 읽습니다(CLI 기본값 5건과 다름). 밀린 실행 없음(catchup=False), 출처별 동시 실행 1개, 전체 동시 실행 8개이며 잠금·이력·재시도는 로컬 수집과 같은 코드를 사용합니다. 다른 실행이 잠금을 보유하면 skipped, 저장 실패는 failed입니다. Airflow는 Windows에서 직접 실행되지 않으므로 WSL에서 실행하며 루트 `.env`의 TiDB 설정을 사용합니다.

```bash
# WSL Ubuntu 최초 1회: Python 3.12 + Airflow 3.4.0 (API용 .venv와 별도)
uv venv --python 3.12 ~/airflow-venv
curl -sfL https://raw.githubusercontent.com/apache/airflow/constraints-3.4.0/constraints-3.12.txt -o ~/airflow-constraints-3.4.0-py3.12.txt
VIRTUAL_ENV=~/airflow-venv uv pip install apache-airflow==3.4.0 pydantic-settings SQLAlchemy "PyMySQL[rsa]" httpx -c ~/airflow-constraints-3.4.0-py3.12.txt
# ~/airflow-env.sh: AIRFLOW_HOME=~/airflow, AIRFLOW__CORE__DAGS_FOLDER=<프로젝트>/pipelines/dags,
#                   AIRFLOW__CORE__LOAD_EXAMPLES=False, AIRFLOW__CORE__PARALLELISM=8
source ~/airflow-env.sh && airflow db migrate
# 새 DAG는 처음에 일시정지일 수 있음: airflow dags unpause <dag_id>
```

실행은 Windows 시작프로그램의 `start-final-airflow.vbs`가 로그인 시 숨김으로 합니다(이미 실행 중이면 건너뜀). AI 작업 도구의 터미널에서 `airflow standalone`을 띄우면 도구가 끝날 때 함께 꺼지므로 운영용으로 쓰지 않습니다.

프로젝트가 이동식 E: 드라이브에 있어 WSL `/etc/fstab`에 `E: /mnt/e drvfs metadata,uid=1000,gid=1000,nofail 0 0`을 등록했습니다. E: 드라이브를 분리하면 DAG가 로드되지 않습니다.
