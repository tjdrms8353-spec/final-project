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
