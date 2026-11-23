# Git workflow

- Use `final-pj` for the owner's development work and `develop` for team integration.
- When the user requests commit/push, update only `final-pj` and `develop`.
- Do not commit, merge, or push to `main` unless the user explicitly requests final release integration.
- Fetch before integration, preserve remote work, and never force-push shared branches.

- 작업과 관련된 파일만 확인한다.
- 기존 기능을 보호한다.
- 다른 팀원 담당 폴더를 임의로 수정하지 않는다.
- 전체 테스트보다 변경 기능 테스트를 우선한다.
- 산출물은 명시적으로 요청한 경우에만 생성한다.
- 작업 완료 후 변경 파일과 테스트 결과만 간략히 보고한다.

## 공통 개발 규칙
- Frontend는 `frontend/`에서 React + Vite, Backend는 `backend/`에서 Python + FastAPI를 사용한다.
- 기능 API는 APIRouter로 분리한다. 경로는 금융 `/api/finance`, 뉴스·SNS `/api/news`, ERP `/api/erp`를 사용한다.
- React는 기능별 페이지·컴포넌트를 분리하며 공통 메뉴·헤더는 메인 웹페이지에서 관리한다.
- React API 호출은 `/api/...` 상대 경로를 사용하고, 개발 환경에서는 Vite 프록시로 FastAPI에 연결한다.
- API Key, DB 접속 정보, 서버 설정은 `.env`로 관리하고 Git에 올리지 않는다. `.env.example`을 제공한다.
- Python 의존성은 `requirements.txt`, React 의존성은 `package.json`으로 관리한다.
- 각자 독립 브랜치 또는 저장소에서 개발하고 통합 시 메인 프로젝트에 병합한다. Git 변경은 명시적인 요청에 따라 수행한다.
- 대용량 ETL, 실시간 수집, 크롤링은 FastAPI API 코드와 분리한다.
- README에 Frontend·Backend 실행 명령어를 유지한다.

## 통합 원칙
- 각자의 FastAPI `main.py`는 로컬 실행용으로 사용하고, 최종 통합 시 메인 서버에 APIRouter를 등록한다.
- 각 팀원의 React 페이지를 메인 React 프로젝트에 추가한다.
- DB 구조와 세부 API 명세는 각자 개발하면서 정하되, 모듈 간 데이터 교환 인터페이스는 통합 전에 협의한다.
- 1주 차에 기본 페이지와 API를 먼저 통합 테스트한다.

## AI 개발 도구 공통 규칙 (Codex·Devin 등)
- 작업 시작 전 `AGENTS.md`, `docs/PROGRESS.md`, `docs/DEVELOPMENT_PLAN.md`, `docs/HANDOFF.md`를 확인한다.
- 기존 개발 계획의 순서를 유지하고, 사용자 지시 없이 개발 단계를 건너뛰지 않는다.
- 한 번에 하나의 개발 단위를 처리한다.
- 기존에 완성한 기능을 손상시키지 않는다.
- 구현 후 관련 테스트를 수행하며, 테스트하지 않은 기능을 완료 처리하지 않는다.
- 작업 완료 후 `docs/PROGRESS.md`와 `docs/HANDOFF.md`를 갱신한다.
- 기존 문서와 실제 코드가 충돌하면 임의로 판단하지 않고 사용자에게 보고한다.
- 외부 수집(`--execute`)·DB 저장(`--store`)·마이그레이션 적용은 사용자 확인 후 실행한다.

## README 규칙 (고정)
- `README.md` 맨 위 "실행 방법 (고정)" 섹션은 항상 첫 섹션으로 유지한다. 실행 방법이 바뀌면 이 섹션을 갱신한다.
- 작업을 마치면 "작업 기록 (날짜순)"의 해당 날짜 아래에 한 줄씩 추가한다. 날짜는 오래된 순서로 쌓고, 근거(Git·문서·파일·검증)를 표시한다.
