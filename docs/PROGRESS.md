# 개발 진행 현황 (PROGRESS)

> 기준일: 2026-11-19 · 작성: Devin (Codex 작업 인수)
> 표기: **[코드확인]** 실제 코드·테스트로 확인 / **[문서확인]** README·로컬작업.md 기록만 존재 / **확인 필요** 근거 부족

## 현재 개발 위치

- 브랜치: `final-pj` (커밋 3개, 마지막 커밋 2026-11-17 `22ec4b2`)
- 2026-11-18 Codex 작업분(뉴스 수집·저장·조회, 마이그레이션, 파이프라인 등)은 **커밋되지 않은 변경 상태**로 작업 폴더에만 존재한다.
- 마지막 작업: 성근 담당 뉴스(trends) 기능 — RSS 수집 → TiDB 저장 → 조회 API → React 목록·상세 화면, 로컬 주기 수집 스케줄러.

## 완료 (테스트로 확인)

| 항목 | 근거 |
| --- | --- |
| 프로젝트 골격(frontend/backend/pipelines/migrations/docs) | [코드확인] |
| FastAPI 메인 + APIRouter 등록(`/api/news`, `/api/finance`, `/api/erp`, 레거시 `/api/v1/*`) | [코드확인] `backend/app/main.py` |
| `/health`, `/api/health`, 각 기능 `/status` | [코드확인] test_health.py |
| TiDB 접속 설정(TLS, `.env`) | [코드확인] `app/core/config.py`, `app/db/session.py` · 실제 접속은 [문서확인] |
| 뉴스 샘플 API `/api/news/sample` | [코드확인] |
| 뉴스 전처리(정규화·중복·검증) | [코드확인] |
| RSS 수집기(bbc-tech, sbs-latest, hankyung-it) + 재시도 | [코드확인] 실제 피드 수집은 [문서확인] 2026-11-18 5건 |
| GDELT 수집기(기본 dry run) | [코드확인] 실제 수집 미실행 |
| 뉴스 저장(URL SHA-256 중복 방지) + 수집 이력(`news_collection_runs`) | [코드확인] |
| 수집 동시 실행 잠금, 중단 이력 interrupted 처리 | [코드확인] |
| 로컬 주기 수집 스케줄러 `schedule_rss` | [코드확인] |
| Alembic 마이그레이션 01~04 (뉴스 테이블·이력·attempt_count·owner) | [코드확인] 파일 존재 · TiDB 적용 여부 **확인 필요** |
| 저장 뉴스 조회 API `GET /api/news`, `GET /api/news/{article_id}` | [코드확인] |
| React 통합 화면(Google AI Studio 데모) + 레거시 HTML iframe | [코드확인] 빌드 통과 |
| React 저장 뉴스 목록·검색·페이지·상세(`StoredNewsView.jsx`) | [코드확인] 빌드 통과 · 브라우저 동작 [문서확인] |

2026-11-19 검증 결과: backend 87 passed, pipelines 42 passed, frontend typecheck·build 통과.

## 진행 중

- **뉴스 2단계 주기적 수집** (순서는 `DEVELOPMENT_PLAN.md`)
  - 로컬 스케줄러 실환경 검증 완료 (2026-11-19, `--cycles 2`, 출처별 1800초)
    - 1회차 UTC 02:27: BBC 신규 5, SBS 신규 5 / 2회차 UTC 02:57: BBC 기존 5(신규 0), SBS 신규 5
    - 모든 실행 success, attempt_count=1 (실제 장애 미발생 → 재시도는 단위 테스트로만 확인)
    - 잠금 보유 중 동시 실행 → `collection_busy`, 외부 요청 없음 확인
    - 잠금은 실행 중에만 보유. 스케줄러 대기 중 별도 수동 수집은 차단되지 않음(설계대로, 1회 수동 실행 기록 존재)
    - `GET /api/news` total 25, 상세 200, Vite 프록시 경유 조회 정상. 화면 표시는 사용자 확인 필요
  - Airflow DAG 코드 작성 (2026-11-19): `pipelines/dags/news_rss_collection.py`, `pipelines/jobs/airflow_rss.py`
    - 단위 테스트 11개 통과 (Airflow 모듈은 스텁으로 대체해 DAG 구조 검증)
  - Airflow 실환경 검증 (2026-11-19, WSL2 Ubuntu 26.04, Python 3.12.16, Airflow 3.4.0 standalone)
    - DAG 2개 import 오류 없이 로드 (`airflow.sdk` 경로 사용)
    - 1회차 예약 실행 UTC 07:10: 두 DAG success. DB: SBS 신규 5, BBC 기존 5, 기사 25→30
    - WSL 내부 잠금 보유 중 수동 실행 → task `skipped` 확인
    - **발견: Windows(msvcrt)와 WSL(flock) 잠금은 서로 공유되지 않음.** Windows 로컬 스케줄러와 Airflow를 동시에 운영하지 않는다. 기사 중복 저장은 URL 기본키로 방지됨
    - 2회차 예약 실행 UTC 07:40 (정확히 30분 후): 두 DAG success. DB: SBS 신규 5, BBC 기존 5, 기사 30→35
    - 수집 이력 7→11건 (예약 4회). skipped 수동 실행은 이력·외부 요청 없음 확인
  - **2단계 완료 (2026-11-19)**: Airflow 출처별 DAG 2회 예약 실행 성공, 이력·신규 건수 확인
  - 발견 (사용자 결정 대기): SBS 속보는 약 3~4분에 1건(피드 101건·약 5시간 40분 분량)인데 30분마다 최신 5건만 수집해 기사 일부 누락. 매 실행 SBS 신규 5건 = 누락 발생 신호. BBC는 `<ttl>15</ttl>`, 기사 수 시간에 1건
    - 제안: `limit` 상향(피드 전체 수집), 출처별 간격(SBS 5분·BBC 15분), 화면 자동 갱신(계획 외)
  - **누락 대응 완료 (2026-11-19)**: Airflow 수집 `FEED_LIMIT = 100` (`pipelines/jobs/airflow_rss.py`)
    - 사전 확인: BBC 21건·SBS 101건 피드 전체가 검증 통과(거부 0), SBS 응답 약 0.8 MB < 2 MiB 제한
    - Airflow 수동 실행 UTC 07:51: SBS 입력 100, 신규 80, 기존 20, 소요 14초. 기사 35→115
    - 피드에 WebSub(hub) 링크 없음 → 출처 측 푸시 수신 불가, 폴링만 가능
    - CLI(`collect_rss`, `schedule_rss`) 기본값 5건은 유지
- 2026-11-18 변경분 Git 커밋: 미수행 (사용자 지시 필요)

## 미완료 / 미시작

| 항목 | 담당 | 상태 |
| --- | --- | --- |
| AI 문서 분류, TOP 10 순위, 감성 분석 | 성근 | 미시작 (`classifiers/`, `ranking/`, `documents/` 빈 폴더) |
| SNS 수집 | 성근 | 미시작 |
| Polars ETL | 성근 | 미시작 (Airflow RSS DAG는 2단계에서 작성) |
| 주식·코인 수집·분석 | 종범 | 미시작 (status만 존재) |
| 영수증 OCR·자동 등록(Playwright) | 승호 | 미시작 (status만 존재) |
| 인증·로그인 | 확인 필요 | 프론트 데모만 존재 |
| 배포(Render, EC2) | 공동 | 미시작 |
| React 데모 화면의 실제 API 연결(뉴스 외) | 프론트엔드 | 미시작 |

## 다음 작업

1. 2단계 마무리: Airflow 실행 환경(WSL 또는 Docker) 준비 → DAG 실행 검증 (사용자 결정: 2단계 완료 후 다음 단계)
   - 2026-11-19: 완료. 누락 대응(limit 100) 완료. 실시간 수집 방식은 사용자 결정 대기
2. **3단계 수집 범위 확대**: 한국 언론사 공식 RSS·이용 조건 조사 → 목록 보고 → 승인된 출처 추가, 출처별 간격(한국 5분·BBC 15분)
   - **3단계 출처 추가 완료 (2026-11-19, 사용자 승인: 1·2번 전체 추가, MBC·KBS·YTN 대안 미사용)**
     - `rss.py`: 출처 9곳 등록, ISO 8601·`dc:date` 날짜 해석, 한겨레 `observed_at`(OBSERVED_TIME_FEEDS), 수집기 User-Agent
     - 오류 해결: 한국경제 403 원인은 라이브러리 기본 UA 차단 → 수집기 식별 UA로 해결(기존 `hankyung-it`도 200)
     - `airflow_rss.py`: 한국 10곳 5분, BBC 15분. `hankyung-it`은 `hankyung-all`에 포함되어 미예약
     - 테스트: backend 90, pipelines 53 통과. 실제 수집 11곳 모두 거부 0건
     - Airflow DAG 11개 로드·실행: 1회차(UTC 08:28~08:30) 신규 539건(기사 115→654), 2회차(08:33~08:35) 모두 success, 기사 694. BBC는 15분 간격(08:10→08:25) 확인
     - 남은 3단계 항목: 분야 추가·기간별 데이터 확보(Codex 원문). 파이낸셜뉴스 갱신 재관찰
   - 남은 3단계 조사 (2026-11-19, 설계 승인 대기)
     - 기사별 `<category>`: 오마이뉴스·경향신문만 분야 정보 제공. SBS는 키워드 태그 혼재(350종), 나머지 없음
     - 공식 분야별 RSS 확인: 연합뉴스(15개), 동아일보(16개), 한국경제(12개), SBS(8개), 연합뉴스TV(10개). 동아일보도 비상업 개인 이용만 허용
     - 피드 보관 시간: 연합TV 0.4h, 뉴시스 0.6h, 한경 0.8h, 연합·오마이 0.9h, 동아 1.8h, 경향 2.1h, SBS 4.8h, 조선 41.8h → PC·USB가 1시간 이상 꺼지면 대부분 출처에서 공백 발생
     - DB 기간: 대부분 2026-11-19 하루치(711건). 과거 데이터 없음
     - GDELT 수집기(기존, 미저장)는 최근 7일·요청당 250건까지 조회 가능 → 공백·과거 보충 후보
   - **분야 추가·수집 공백 기록 구현 (2026-11-19~23, 사용자 결정: 분야 피드+저장, 공백 기록. GDELT 보충은 하지 않음)**
     - 마이그레이션 `20261119_05`(개인 TiDB 적용): `news_article_sections`(기사별 언론사 분야 원문), `news_collection_runs.window_start_at`
     - 분야 피드 41개(연합 10·동아 8·한경 10·SBS 7·연합TV 6) 30분 간격 + 오마이·경향 피드 내 `<category>`. 분야 이름 통일은 5단계에서
     - `GET /api/news/coverage?hours=24&feed=`: missed(보관 범위가 직전 수집과 끊김)·unverified(보관 범위 기록 없음+간격 1h 초과)·ongoing(최근 수집 멈춤)
     - Airflow DAG 52개, 동시 실행 8개 제한(`AIRFLOW__CORE__PARALLELISM=8`)
     - 검증(2026-11-23 UTC 07:10 이후): 86회 성공·52개 DAG 전부 동작, 신규 873건, 분야 2,754건. 11-19~11-23 PC 중단 공백을 missed로 정확히 검출
     - 실패 1건: `yna-all` 07:11 `database_write`(연합 전체+분야 11개 동시 실행 시각, 다음 실행 정상, 피드 보관 0.9h라 손실 없음). 원인 확인을 위해 DB 오류 번호 기록 추가(`database_write_<번호>`). 재발 시 원인 확인 후 대응
     - 테스트: backend 94, pipelines 55 통과
     - **발견·해결: Airflow를 작업 도구 터미널에서 실행하면 터미널 종료 시 WSL과 함께 종료됨**(11-19~23 수집 중단 원인). Windows 시작프로그램 `start-final-airflow.vbs`로 로그인 시 숨김 자동 실행
   - **3단계 완료 (2026-11-23 사용자 확인)**. 남은 확인(선택): RSS 이용 조건 미확인 7곳(한경·뉴시스·조선·오마이·경향·한겨레·BBC), 분야 조회 API·화면 없음(5단계에서 사용), 파이낸셜뉴스 갱신 재관찰
3. **4단계 해외 뉴스 자동 번역 (2026-11-23 착수)** — 사용자 결정: DeepL API, 제목+요약
   - 조사: BBC 월 약 1.2만 자. DeepL 무료 Developer 플랜 총 100만 자(비갱신), Papago는 유료(100만 자당 약 2만 원), 로컬 모델 `opus-mt-tc-big-en-ko`는 무료지만 품질 낮고 약 1GB 설치
   - 구현: BBC 요약 저장(`SUMMARY_FEEDS`, 빈 요약만 채움), `translation.py`, `translate_news.py`, 마이그레이션 `20261123_06`(적용), DAG `news_translate_ko` 15분, API `title_ko`·`summary_ko`, 화면 번역 표시
   - 테스트: backend 106, pipelines 60 통과. Airflow DAG 53개 로드
   - 실환경 검증(2026-11-23 UTC 08:29): `.env`의 `DEEPL_API_KEY` 인식 확인(값 미출력). Airflow `news_translate_ko` 최근 2회 success, BBC 34건 중 번역 25건(제목 25·요약 14), 미번역 9건(원문 요약 있음 7·없음 2). API 목록/상세에서 한국어·원문 필드 동시 반환 200, 프론트 프록시 200. 수동 DeepL 요청은 실행하지 않음
   - 429·5xx 최대 2회 지수 백오프 재시도(1초·2초), 400·456 재시도 없음. MockTransport 테스트 포함 backend 관련 36건·pipelines 관련 5건 통과, 프론트 typecheck·build 및 Python compileall 통과(빌드 번들 크기 경고)
   - 당시 대기 9건은 다음 예약 실행으로 처리됨(아래 참조). 화면 직접 확인 후 4단계 완료 판단. DeepL 요청/DB 저장이 있는 수동 `--execute`는 별도 사용자 확인 없이 실행하지 않음
   - 2026-11-23 UTC 08:35 Airflow 예약 실행 success: BBC 34건 모두 제목 번역, 원문 요약이 있는 21건 모두 요약 번역, 미번역 0건. API `source=BBC News` 34건/최신 5건 번역 확인. 화면 직접 확인은 사용자 대기. 출처 필터는 정확히 일치하므로 `bbc` 입력 시 0건
   - 2026-11-19 실측 기록(피드당 1회, 기존 검증 규칙 적용, DB 저장 없음)
     - 바로 사용 가능: 연합뉴스(약 146건/h), 연합뉴스TV, 동아일보, 한국경제(all-news), 뉴시스(`www.` 주소), 조선일보
     - 파서 보완 필요: 오마이뉴스(ISO 8601 날짜), 경향신문(`dc:date`), 한겨레(기사별 날짜 없음 → 관측 시각 필요, 주소는 `/rss`)
     - 제외: MBC·KBS·YTN(RSS 폐지), JTBC(2024-10 이후 갱신 중단), 매일경제(403), 파이낸셜뉴스(최신 기사 약 8시간 전, 갱신 지연 의심)
3. 이후 4 번역 → 5 분류 → 6 이슈 묶기 → 7 SNS → 8 TOP 10 → 9 문서 분석 → 10 배포 (`DEVELOPMENT_PLAN.md`, 2026-11-19 사용자 확정)
