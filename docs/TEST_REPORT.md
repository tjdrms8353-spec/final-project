# 테스트 보고서 (TEST_REPORT)

작성일: 2026-11-25 | 정식 전환 B 보완 + 정식 전환 C 기준

## 전체 결과

- **pytest: 94/94 통과** (기존 69 + 신규 25)
- 실행: `C:/venvs/dayribbon/Scripts/python.exe -m pytest tests` (USB 소스에서 실행)
- 프론트엔드: `npx vite build` 통과 (로컬 작업공간 `C:\dayribbon-build`)

## 테스트 파일 구성

| 파일 | 건수 | 범위 |
|---|---|---|
| `test_api.py` | 23 | 인증·권한·재무CRUD·제품/거래처/원자재·업로드·대시보드·알림·감사·시뮬레이션 |
| `test_onboarding.py` | 16 | 회원가입·기업등록·초대·권한·비밀번호 변경/재설정·격리 |
| `test_collectors.py` | 30 | 수집기 파싱·공통 저장·중복 방지·점수 독립성·스케줄·API 권한 |
| `test_phase_c.py` | 25 | KPI·위험 평가·LLM·자동 분석·마이그레이션 |

## 정식 전환 B 보완 검증 (§2·§5 완료 조건)

- 공통 외부 데이터 1회 저장 — `company_id=NULL` 행 확인, 기업 2개 조회 시 중복 없음
- 기업별 관련도 점수 독립성 — 같은 뉴스에 서로 다른 점수 유지
- 수집기 상태/이력 — `collector_states`·`collection_runs` 기록, `due_collectors` 주기 준수
- 수집 API 권한 — 비로그인 401, VIEWER 403, ADMIN 성공
- 뉴스 API 공통+기업 점수 병합, 교차 기업 접근 차단

## 정식 전환 C 검증 (§24 필수 테스트)

| 요구 항목 | 테스트 | 결과 |
|---|---|---|
| KPI 계산·기간 비교 | 매출/이익률/성장률·부채비율·유동비율 값 검증 | ✅ |
| Decimal 정확성 | 소수 계산 오차 없이 비교 | ✅ |
| 데이터 부족 처리 | 미입력 KPI → `insufficient_data` (0 대체 없음) | ✅ |
| 0 나눗셈 방지 | 매출 0 → `not_computable` | ✅ |
| 수출/수입 기업 영향 차이 | 동일 환율 변동에 상반된 위험 점수 | ✅ |
| 위험 등급 | 정상~심각 + `판단 보류` 구분 | ✅ |
| LLM 정상 응답 | Mock HTTP → JSON 검증 → 분석 저장·`llm_calls` 기록 | ✅ |
| LLM 비정상 응답 | JSON 파싱 실패 → 규칙 폴백 | ✅ |
| LLM 호출 제한 | 429 → 백오프 재시도 → 성공 | ✅ |
| 규칙 폴백 | 키 없음/실패/예산 초과 시 `engine=rule-based` 표시 | ✅ |
| 중복 분석 방지 | 동일 데이터 서명 → `analysis_jobs` skipped | ✅ |
| 기업 데이터 격리 | 다른 기업 KPI/뉴스 접근 차단 | ✅ |
| 민감정보 노출 방지 | LLM 프롬프트에 토큰·키 미포함 | ✅ |
| 악성 지시 무시 | 뉴스 내 지시문 sanitize 후 `untrusted_data` 격리 | ✅ |
| 신규 데이터 자동 분석 | 업로드·프로필 변경 트리거 → 분석 생성 | ✅ |
| AI 옵트인 | `allow_external_ai=False` → LLM 미호출 | ✅ |
| 마이그레이션 | upgrade→downgrade→upgrade SQLite 검증 | ✅ |

## 실연동 vs Mock 구분

| 기능 | 실연동 | Mock 검증 |
|---|---|---|
| RSS 뉴스 | ✅ 30건 실수집 (단계 B) | — |
| GDELT | 부분 — HTTP 200·기사 수신 확인, 저장 경로는 공급처 레이트리밋(1req/5s)으로 재검증 대기 | 파싱·저장 경로 |
| EXIM/ECOS/FRED/EIA/DART | 키 대기 | ✅ 응답 파싱·저장 |
| LLM | 키 대기 | ✅ 호출·검증·폴백·비용기록 |
| TiDB | 접속 정보 대기 | SQLite 마이그레이션 검증 |
