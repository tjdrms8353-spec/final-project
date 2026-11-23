# AI 개발 인수인계 (HANDOFF)

> 작업 시작 전 `AGENTS.md` → `docs/PROGRESS.md` → `docs/DEVELOPMENT_PLAN.md` 순서로 확인한다.

## 작업 위치

- 개발 기준 폴더: `E:\송성근(심화)\finalProject\Finalproject-main` (Git 저장소)
- 바깥 `finalProject/README.md`, `로컬작업.md`는 통합 전 기록이며 개발 기준이 아니다.
- 바깥 `finalProject/google-ai-studio/`는 프런트엔드 데모의 원본이며 이미 `frontend/`에 통합되었다.
- 브랜치: 개인 작업 `final-pj`, 팀 통합 `develop`. `main`은 명시적 요청 없이 건드리지 않는다.

## 기술 스택

| 영역 | 기술 |
| --- | --- |
| Frontend | React 19, Vite 7, Tailwind 4, TypeScript 5.9(일부 .tsx), Recharts, lucide-react |
| Backend | Python 3.12, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, PyMySQL, httpx |
| DB | TiDB (MySQL 호환, TLS) · 테스트는 SQLite |
| 파이프라인 | `pipelines/` (WSL Airflow 3.4.0, RSS·번역 DAG; Polars ETL은 미시작) |
| 기타 | Docker Compose, GitHub Actions CI (frontend typecheck·build, Python compileall) |

## 핵심 파일

| 파일 | 역할 |
| --- | --- |
| `backend/app/main.py` | FastAPI 앱, 라우터 등록, CORS, `/health` |
| `backend/app/core/config.py` | `.env` 설정 (TiDB, CORS) |
| `backend/app/db/session.py` | TiDB 엔진·세션 |
| `backend/app/features/trends/router.py` | 뉴스 API (`/status`, `/sample`, 목록, 상세) |
| `backend/app/features/trends/collectors/` | RSS·GDELT 수집기, 재시도 |
| `backend/app/features/trends/repository.py` | 뉴스 저장·검색 |
| `backend/app/features/trends/models.py` | `news_articles`, `news_collection_runs` |
| `pipelines/jobs/collect_rss.py` | RSS 수집 CLI (기본 dry run) |
| `pipelines/jobs/schedule_rss.py` | 로컬 주기 수집 |
| `pipelines/jobs/airflow_rss.py` | Airflow 작업 로직 (Airflow 미설치 상태에서도 테스트 가능) |
| `pipelines/dags/news_rss_collection.py` | 출처별 RSS DAG (30분, catchup 없음) — 실제 Airflow 실행 미검증 |
| `pipelines/jobs/rss_history.py`, `collection_lock.py` | 수집 이력, 동시 실행 잠금 |
| `migrations/versions/` | Alembic 01~04 |
| `frontend/src/App.jsx` | 탭 기반 메인 화면 |
| `frontend/src/components/StoredNewsView.jsx` | 실제 DB 뉴스 화면 |
| `frontend/src/components/*View.tsx` | AI Studio 데모 화면 (가상 데이터) |
| `frontend/public/legacy/` | 기존 AutoFlow HTML |

## 실행 및 테스트

자세한 절차는 `로컬작업.md`. 요약 (프로젝트 루트, PowerShell):

```powershell
.\.venv\Scripts\python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8001
cd frontend; npm.cmd run dev -- --host localhost --port 5175 --strictPort

.\.venv\Scripts\python -m pytest -c backend/pytest.ini backend/tests
.\.venv\Scripts\python -m pytest -c pipelines/pytest.ini pipelines/tests
cd frontend; npm.cmd run typecheck; npm.cmd run build
```

2026-11-19 결과: backend 87 passed, pipelines 42 passed, typecheck·build 통과.

## 미해결 문제 및 주의사항

1. **2026-11-18 작업분이 Git에 커밋되지 않았다.** 수집·저장·조회·마이그레이션·테스트 대부분이 미추적(`??`) 또는 수정(`M`) 상태다. 커밋은 사용자 지시 시에만 한다.
2. 문서 간 테스트 수 불일치: `로컬작업.md`는 backend 51개·pipelines 18개로 기록, 현재는 87개·42개. 이후 테스트가 추가된 것으로 보이며 문서 갱신이 필요하다 (사용자 확인 후).
3. `trends/service.py`의 `get_status()`는 여전히 `not_implemented`를 반환한다. 실제 기능과 맞지 않는다.
4. 한국경제는 라이브러리 기본 UA(`python-httpx`)를 403으로 차단한다. 수집기는 `USER_AGENT`(`rss.py`)를 보낸다. 직접 `httpx.Client`를 넘길 때는 UA를 따로 지정해야 한다.
5. SBS·연합뉴스·연합뉴스TV RSS는 비상업적 개인 이용만 허용된다(동아·한경·뉴시스·조선·오마이·경향·한겨레는 이용 조건 확인 필요). 제목·링크·날짜만 저장하고 본문은 수집하지 않는다.
6. 수집 잠금은 단일 PC 기준이다. 분산 잠금은 지원하지 않는다.
7. 프런트엔드 번들이 768 kB로 500 kB 경고가 있다. 코드 분할은 하지 않았다.
8. TestClient의 httpx 사용 폐기 예정 경고 1건.
9. React 데모 화면(금융·OCR·문서 AI·DataOps·로그인)은 모두 `mockDb.ts` 가상 데이터다.
10. `frontend/src/services/api.js`는 `fetch` 기반이다. 문서는 "공통 Axios 클라이언트"라고 기술하지만 Axios는 의존성에 없다.
11. 마이그레이션의 공유 TiDB 적용 여부와 팀 스키마 검토 여부가 확인되지 않았다. (개인 TiDB는 `20261118_04` 적용 확인)
12. Airflow는 WSL2 Ubuntu에서 실행한다 (Airflow 3.4.0, Python 3.12, `~/airflow-venv`, 설정 `~/airflow-env.sh`, 메타DB SQLite `~/airflow`). `pipelines/requirements.txt`의 `apache-airflow`는 아직 버전 미고정이다(검증 버전 3.4.0).
13. Windows(msvcrt)와 WSL(flock) 수집 잠금은 공유되지 않는다. 로컬 스케줄러와 Airflow를 동시에 운영하지 않는다. 수집 이력 `owner_id`도 Windows·WSL이 서로 다르다.
14. 프로젝트가 이동식 E: 드라이브(FAT32)에 있다. WSL은 `/etc/fstab`으로 `/mnt/e`에 마운트한다. 드라이브 분리 시 Airflow DAG 로드가 실패한다.
15. WSL 명령을 Windows에서 보낼 때 PowerShell·Git Bash가 `$`, `|`, 따옴표를 변형한다. 여러 줄 명령은 스크립트 파일로 만들어 `wsl --exec bash 스크립트`로 실행한다.
16. Airflow는 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\start-final-airflow.vbs`가 Windows 로그인 시 숨김 실행한다(이미 실행 중이면 건너뜀, 검사 패턴 `[b]in/airflow standalone`). AI 작업 도구의 터미널에서 `airflow standalone`을 띄우면 도구 종료 시 WSL과 함께 꺼지므로 운영용으로 쓰지 않는다. 중지: `wsl -d Ubuntu --exec pkill -f "bin/airflow standalone"`.
17. 수집 공백은 `GET /api/news/coverage`로 확인한다. 8단계 급상승 계산에서 missed·unverified·ongoing 구간을 제외해야 한다.
18. 번역: `DEEPL_API_KEY`(루트 `.env`, `:fx`로 끝나면 api-free 주소)가 비면 `news_translate_ko`는 skipped. 429·5xx는 1초·2초 백오프 후 최대 2회 재시도, 400·456은 즉시 실패하며 다음 예약 실행에서만 재시도한다. 원문은 `news_articles`, 번역은 `news_translations(lang='ko', provider)`에 분리 저장한다. 키 값·본문을 로그에 남기지 않는다.
19. 2026-11-23 초기 실환경 검증: Airflow 번역 DAG 2회 success, BBC 34건 중 번역 25건(제목 25·요약 14), 당시 미번역 9건. 뉴스 API 목록·상세에 원문+한국어 필드가 함께 반환됨(200). 프론트 개발 프록시 200, typecheck·build 통과. 수동 `--execute`는 미실행.
20. 같은 날 UTC 08:35 예약 실행 success 후 BBC 34건 제목 모두 번역·원문 요약 21건 모두 번역·미번역 0건. 출처 필터는 완전 일치(`source=BBC News` 34건, `source=bbc` 0건); 화면 직접 확인은 아직 사용자 대기.

## 다른 AI가 이어받을 때

- 성근 담당 `trends/`·`pipelines/` 외의 팀원 폴더(`finance/`, `receipts/`)는 수정하지 않는다.
- 외부 수집(`--execute`)과 DB 저장(`--store`)은 실행 영향이 있으므로 사용자 확인 후 실행한다.
- `.env`, `frontend/.env`는 Git에 올리지 않는다.
- 작업 후 `docs/PROGRESS.md`와 이 문서를 갱신한다.
