# 분석 모델 문서 (ANALYSIS_MODEL)

작성일: 2026-11-25 | 정식 전환 C 기준

## 분석 파이프라인

```
기업 내부 데이터 + 공통 외부 데이터
 → 데이터 품질 검증 (결측·0 대체 금지)
 → Python 기반 수치 계산 (kpi_service, Decimal)
 → 기업별 위험·기회 평가 (risk_service, 수출입 구조 반영)
 → LLM 해석 (llm_provider, 옵트인 기업만) 또는 규칙 기반 엔진
 → 구조화된 분석 결과 (AnalysisResult)
 → 관리자 검토 (status: 검토 대기 → 수용/보류/미수용)
```

- 수치 계산은 절대 LLM에 맡기지 않는다. LLM은 검증된 계산 결과의 해석·대응 제안만 수행.
- 근거 없는 수치·출처·신뢰도 점수를 생성하지 않는다.
- LLM 실패·옵트아웃·예산 초과 시 규칙 기반 엔진 폴백 — `engine` 필드로 구분한다
  (`llm:{model}` vs `rule-based`/`rule-based-demo`). 폴백 결과를 LLM 분석으로 표시하지 않는다.

## KPI 계산 기준 (kpi_service.compute_kpi_report)

모든 지표는 `status`를 가진다: `ok` / `insufficient_data` / `not_computable`(분모 0).
데이터가 없으면 0으로 대체하지 않고 미입력 컬럼은 NULL로 저장한다.

| 지표 | 계산식 | 입력 |
|---|---|---|
| 매출액 | 당월 revenue | financial_monthly |
| 영업이익 | 당월 operating_profit | financial_monthly |
| 순이익 | 당월 net_income | financial_monthly (미입력→부족) |
| 영업이익률 | 영업이익 ÷ 매출 × 100 | 상동 |
| 순이익률 | 순이익 ÷ 매출 × 100 | 상동 |
| 매출 성장률(전월) | (당월−전월) ÷ 전월 × 100 | 상동 |
| 매출 성장률(전년동월) | (당월−전년동월) ÷ 전년동월 × 100 | 13개월 필요 |
| 비용 증가율 | (비용합계_당월−전월) ÷ 전월 × 100 | 원자재+인건비+기타 |
| 부채비율 | 부채총계 ÷ 자본총계(자산−부채) × 100 | assets·liabilities |
| 유동비율 | 유동자산 ÷ 유동부채 × 100 | current_assets·current_liabilities |
| 제조원가 | 원자재비 + 인건비 | 상동 |
| 원자재 구매 비용 | 당월 raw_material_cost | 상동 |
| 재고 회전율 | 제조원가 ÷ 재고자산 | inventory |
| 제품별 수익성 | (제품 매출−원가) ÷ 매출 × 100 | product_monthly |
| 거래처 의존도 | 최대 거래처 최근 3개월 매출 ÷ 합계 × 100 | customer_monthly |
| 수출 비중 | 수출액 ÷ 매출 × 100 | financial_monthly |
| 수입 비중(비용 대비) | 수입액 ÷ 비용합계 × 100 | 상동 |
| 외화 결제 비중 | 외화 구매액 ÷ 총 구매액 × 100 (없으면 프로필 값) | material_purchases / company |

기간 비교는 동일 '월' 단위만 비교한다 — 서로 다른 회계 기간·단위를 혼합하지 않는다.

## 위험 평가 기준 (risk_service.assess_risks)

점수 0~100 → 등급 매핑:

| 점수 | 등급 |
|---|---|
| 80~100 | 심각 |
| 60~79 | 위험 |
| 40~59 | 주의 |
| 20~39 | 관심 |
| 0~19 | 정상 |
| — | 판단 보류 (데이터 부족 — '정상'이 아님) |

카테고리별 평가식:

| 카테고리 | 점수 산정 | 기업 맞춤 요소 |
|---|---|---|
| 환율 | 수입 중심: 상승변동×15 + 수입노출×0.5 / 수출 중심: 하락변동×15 + 수출노출×0.5 / 불명확: \|변동\|×15 | 수출입 구조(trade_direction) |
| 금리 | 금리상승(%p)×40 + 차입금/월매출×0.3 | 차입금 규모 |
| 원자재 가격 | 원자재비/매출×0.8 + WTI 상승×5 | 원자재 비중 |
| 수익성 | 이익률 하락(%p)×12 + 마이너스 이익률×3 | — |
| 매출 | 매출 감소율(전년동월 우선, 없으면 전월)×8 | — |
| 거래처 집중 | 최대 거래처 비중×1.5 | — |
| 재고 부담 | 재고자산/월매출×0.8 | — |
| 재무 안정성 | (부채비율−100)×0.4 + (100−유동비율)×0.4 / 자본≤0이면 100 | 자산·부채·유동 항목 |

수출입 구조 추정: 실데이터(export_amount vs import_amount) 우선, 없으면 프로필 `export_import_ratio`.

## LLM 호출·비용 관리

- 엔드포인트: OpenAI 호환 `{LLM_BASE_URL}/chat/completions` (공급처 교체 가능).
- 옵트인: `companies.allow_external_ai` — 미승인 기업은 호출 자체를 하지 않는다.
- 전송 최소화: 검증된 KPI·위험 평가·프로필 라벨 + 뉴스 메타(제목·카테고리·관련도)만.
  비밀번호·토큰·키·다른 기업 데이터는 구조적으로 제외.
- 인젝션 가드: 외부 데이터는 `<untrusted_data>`로 격리 + 제어 문자/지시형 패턴 제거(`sanitize_untrusted`).
- 응답 검증: JSON → Pydantic `LlmAnalysisResponse` (growth/direction/risk 각 필수 필드).
- 재시도: `LLM_MAX_RETRIES`(기본 1) — 429·5xx는 지수 백오프 재시도.
- 기록: `llm_calls` 테이블에 토큰·지연·상태(ok/error/skipped_budget) 저장. 금액은 미확정.
- 예산: `LLM_MONTHLY_TOKEN_BUDGET`(0=무제한) 초과 시 자동 폴백.

## 자동 분석 트리거 (§18)

| 트리거 | 발생 시점 | 중복 방지 |
|---|---|---|
| `upload` | 재무 데이터 저장·CSV 업로드 | 데이터 내용 해시 서명 dedup_key |
| `profile` | 기업 프로필 변경 | 사용자 직접 변경 — force 실행 |
| `collect` | 신규 시계열 또는 관련도≥70 뉴스 수집 | 데이터 서명 dedup_key |
| `schedule` | 24시간 경과 | 스케줄러 최신성 검사 |
| `manual` | 사용자 수동 실행 | force 실행 |

작업 이력은 `analysis_jobs`(trigger/dedup_key/status/result_count/error)에 기록된다.

## 시뮬레이션 (§16)

기존 시뮬레이션 엔진(`services/simulation` 관련 로직·`/api/simulation`)을 재사용한다.
환율·금리·원자재·매출 변동 시나리오를 동일 조건에서 재현 가능한 결정적 계산으로 수행하며,
환헤지·고정/변동금리 등 미확인 조건은 가정으로 명시한다.
