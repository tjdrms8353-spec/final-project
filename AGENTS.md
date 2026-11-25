# dayribbon — 개발 에이전트 지침

이 프로젝트는 AI 기반 중소기업형 맞춤형 BI 시스템의 데모/정식화 단계 코드베이스입니다.

## 소통
- 모든 작업 보고·주석·커밋 메시지 설명은 한국어로 작성합니다.
- 기술 용어·파일명·코드는 원문 유지.

## 프로젝트 구조
- `backend/` — FastAPI + SQLAlchemy (SQLite, 정식 전환 시 TiDB/MySQL 대비 ORM 분리)
  - `app/models.py` — 전체 테이블 (18개)
  - `app/routers/` — 기능별 API 라우터
  - `app/services/` — 분석엔진(규칙 기반)·시뮬레이션·보고서 PDF
  - `app/seed.py` — 데모 데이터 생성기
  - `tests/` — pytest API 테스트
- `frontend/` — React 18 + Vite + Tailwind v4 + Recharts
  - `src/api.js` — 단일 API 클라이언트 (토큰은 localStorage)
  - `src/auth.jsx` — 인증 컨텍스트
  - `src/pages/` — 화면 13개
  - `src/components/` — Layout, ui (공통 컴포넌트, ErrorBoundary 포함)
- `docs/` — 설계·전환 계획·개발 진행 문서
- `sample-data/` — 업로드 테스트용 CSV

## 개발 원칙
1. 기존 완료 기능을 임의로 변경·삭제하지 않습니다.
2. 정식 전환은 `docs/DEVELOPMENT_PLAN.md`의 20단계 계획을 따릅니다.
3. 완료/미완료 상태는 `docs/DEVELOPMENT_PROGRESS.md`에 즉시 갱신합니다.
4. 데모 데이터와 실제 데이터를 명확히 구분합니다(화면·문서에 표기).
5. AI/LLM이 실제 동작하지 않으면 "규칙 기반 분석"이라고 명시합니다.
6. 최종 의사결정은 항상 사람이 수행합니다(AI는 제안만).
7. 새 설정·기능은 `.env.example`에 문서화합니다.
8. 비밀번호·키를 코드에 하드코딩하지 않습니다.
9. 기존 다른 프로젝트(ERP 등)와 연동하거나 수정하지 않습니다.
10. GitHub 푸시·외부 배포는 지시 없이 수행하지 않습니다.

## 실행/테스트 명령어
```powershell
# 초기 설치
.\setup.ps1
# 실행 (백엔드+프론트엔드, 포트 자동 선택)
.\start.ps1
# 종료
.\stop.ps1
# 백엔드 테스트
backend\.venv\Scripts\python.exe -m pytest backend/tests -v
# 프론트엔드 빌드 검증
cd frontend && npx vite build
```

## 주의 사항
- `demo_events` 라우터는 데모 전용 — 프로덕션 노출 시 실데이터 오염 가능(feature flag 격리 예정).
- `users.email` 같은 컬럼명 한글 별칭은 업로드 검증에서 지원됨.
- 보고서 PDF는 한글 폰트(맑은고딕 등)가 있어야 출력됨.
