# dayribbon BI 작업 기록

> 표기: **(검증)** 테스트·실행으로 확인 / **(미검증)** 코드만 작성 / **(미구현)** 아직 없음

## 1. 저장소 이전

| 항목 | 상태 |
| --- | --- |
| 기존 저장소 `tjdrms8353-spec/final-project` | 유지 (삭제·변경 없음) |
| 신규 저장소 `tjdrms8353-spec/dayribbon` (private) | 사용자 생성 대기 → 생성 후 `main`·`develop`·`final-pj` 전체 이력 push |
| 민감정보 점검 | 전체 Git 이력에 `.env` 파일 없음, API 키·토큰 패턴 검색 결과 없음 (검증) |
| 태그 | 기존 저장소에 태그 없음 |
| Render/EC2 | 새 저장소 정상 동작 확인 전까지 변경하지 않음 |

## 2. 기존 기능 분석 결과

- 유지: 뉴스 RSS 수집·저장·번역(DeepL), 뉴스 조회 API, Airflow DAG, 기존 React 화면(뉴스·금융·문서·OCR·운영 데모), 레거시 HTML 화면
- 재사용: 저장 뉴스 테이블(`news_articles`)을 BI 분석의 산업 뉴스 근거로 연결 (중복 수집기 미개발)
- 기존 금융(`/api/finance`)·OCR(`/api/erp`)은 상태 API scaffold만 있어, BI는 별도 `/api/bi` 라우터로 추가

## 3. 구현 내용

| 기능 | 위치 | 상태 |
| --- | --- | --- |
| 회원가입·로그인 (PBKDF2 해시, HMAC 서명 토큰) | `backend/app/features/bi/security.py` | 검증 |
| 기업 등록 (기업명·업종·주요 제품·관심 산업·거래 국가·관심 금융지표) | `router.py`, `CompanyForm.jsx` | 검증 |
| 업종 템플릿 구조 + 반도체 제조 템플릿 (KPI 9개, 뉴스 키워드, 시장지표, 임계값) | `industries.py` | 검증 |
| 기업별 권한 OWNER·APPROVER·ANALYST·VIEWER, 결정은 OWNER·APPROVER만 | `router.py` | 검증 |
| ERP CSV(UTF-8/CP949)·Excel(.xlsx) 업로드, 한국어/영어 열 이름, 행 단위 오류 보고, 10MB·5만 행 제한 | `erp_import.py`, `UploadPanel` | 검증 |
| 월별 KPI 계산 (Polars), 매출 추세 (scikit-learn 선형회귀) | `metrics.py` | 검증 |
| 환율 수집 (Frankfurter·ECB 기준환율, 무료) USD·JPY·CNY·EUR/KRW, 출처 URL 저장 | `market.py` | 검증 (실제 API 258건 수집 확인) |
| 맞춤 대시보드 (KPI 카드, 월별 차트, 환율 차트, 관련 뉴스) | `BiDashboard.jsx` | 빌드·로그인 화면 렌더 확인, 전체 UI 흐름 미검증 |
| 근거 기반 기회·위험 분석: 확인된 사실 / AI 추론 / 근거·출처 / 불확실성 / 검토사항 / 권고 분리 | `analysis.py`, `AnalysisPanel.jsx` | API 검증 |
| LLM 서술 (선택, OpenAI 호환). 검증된 사실에 없는 숫자가 나오면 폐기하고 템플릿 사용 | `analysis.py` | 단위 테스트만 (실제 LLM 호출 안 함) |
| 관리자 승인·보류·반려, 결정 사유, 담당자, 기한, 후속 조치, 결정 이력 | `router.py`, `DecisionsPanel.jsx` | API 검증 |
| 시나리오 시뮬레이션 (환율·매입단가·판매단가·판매량) — 2차 기능 베타 | `simulation.py`, `SimulationPanel.jsx` | API 검증 |
| DB 마이그레이션 (BI 테이블 10개) | `migrations/versions/20261124_07_bi_platform.py` | 미검증 (TiDB 적용 안 함) |
| 반도체 샘플 ERP 데이터 (6개월, 48행) | `frontend/public/samples/semiconductor_erp_sample.csv` | 검증 |
| 브랜드명 `dayribbon` (상단 로고, 제목, 푸터, 인증창, API 이름) | frontend, `.env.example` | 빌드 확인 |

## 4. 분석 원칙

1. 모든 수치는 SQL·Polars·scikit-learn으로 계산하고 `facts`에 출처·기간과 함께 저장한다.
2. AI 추론(`inference`)과 권고(`recommendation`)는 별도 필드로 화면에서 구분 표시한다.
3. 뉴스·환율 근거는 저장된 데이터의 실제 제목·URL·출처만 사용한다.
4. LLM은 검증된 사실을 설명하는 용도로만 쓰며, 새 숫자를 만들면 결과를 버린다.

## 5. 외부 API 비용

| API | 용도 | 비용 | 비고 |
| --- | --- | --- | --- |
| Frankfurter (ECB) | 환율 | 무료, 키 불필요 | 영업일 기준 일 1회 갱신 |
| DeepL | 기존 뉴스 번역 | 기존 설정 유지 | 변경 없음 |
| OpenAI 호환 LLM | 분석 요약 서술 | 유료 (키 설정 시에만 호출) | 기본값 비활성. 무료 대안: 템플릿 서술(기본), 로컬 Ollama의 OpenAI 호환 엔드포인트(`LLM_BASE_URL`) |
| 한국은행 ECOS (기준금리) | 금리 지표 | 무료 (키 필요) | 미연동. 현재는 `POST /api/bi/market/indicators`로 수동 입력 |

## 6. 테스트 결과 (2026-11-24)

- backend: 112 passed (기존 109 + BI 3개 통합 시나리오) (검증)
- pipelines: 60 passed (검증)
- frontend: `npm run typecheck`, `npm run build` 통과 (번들 크기 경고) (검증)
- 로컬 SQLite + 실제 Frankfurter API로 회원가입 → 기업 등록 → 샘플 업로드 48행 → KPI 9개 → 분석 3건(매출 감소·이익률 하락·재고 과다) 생성 확인 (검증)

## 7. 미완료·제약

- 신규 GitHub 저장소 생성 및 이력 이전 (사용자 생성 대기)
- BI 화면 전체 흐름의 브라우저 테스트 (로그인 화면 렌더만 확인)
- TiDB에 마이그레이션 07 적용 및 운영 DB 검증
- Render/EC2 배포 검증
- Airflow에서 환율 자동 수집 DAG (현재는 화면의 ‘환율 최신화’ 버튼으로 수동 수집)
- 한국은행 기준금리 등 추가 금융지표 자동 수집
- 반도체 외 업종 템플릿 (구조는 `INDUSTRIES`에 추가하면 확장)
- 기존 상단 데모 RBAC·인증창은 데모 상태 그대로이며, BI 탭만 실제 인증 사용
- 시장지표 수동 입력 API는 로그인 사용자 누구나 호출 가능 (전역 관리자 역할 도입 필요)
