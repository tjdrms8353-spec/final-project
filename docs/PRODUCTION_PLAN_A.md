# dayribbon 정식 전환 계획 — 단계 A~E

작성일: 2026-11-25
근거: `PRODUCTION_TRANSITION_PLAN.md`, 정식 전환 A 개발 지시서

> 20단계 데모 계획(`DEVELOPMENT_PLAN.md`)과 별개의 정식 전환 단계.
> 원본 데모 `dayribbon-bi-demo`는 보존, 본 프로젝트(`dayribbon`)에서 전환을 진행한다.

| 단계 | 내용 | 상태 |
|---|---|---|
| A | 기반 시스템: TiDB 연결 모듈·Alembic·회원가입·온보딩·워크스페이스·권한·격리 | ✅ 완료 (TiDB 실접속 제외 — 접속 정보 대기) |
| B | 실제 데이터 수집: EXIM/ECOS/뉴스 어댑터 구현·스케줄 수집·출처 표기 | ✅ 완료 + 보완 (공통 데이터 구조·수집기별 스케줄·GDELT/FRED/EIA/DART·이용 조건 문서화 — `DATA_SOURCES.md`·`DATA_LICENSES.md`) |
| C | BI·AI 경영 분석: KPI 계산·위험 평가·LLM 실구현·자동 분석 | ✅ 완료 (`ANALYSIS_MODEL.md` — LLM 실호출·TiDB 실접속은 키/접속 정보 대기) |
| D | 발송·운영: 이메일/카카오 실발송, 관측, 배포 파이프라인 | ⬜ |
| E | UI/UX 고도화: 디자인 토큰 기반 전면 개편 | ⬜ 기능 완료 후 |
