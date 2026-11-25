# 데이터 공급처 이용 조건 검토 (DATA_LICENSES)

검토일: 2026-11-25
검토 기준 항목: 상업적 이용 / 저장 / 가공 / AI 분석 / 제3자 제공·재배포 / 출처 표시 / 보존 기간 / 호출 제한

> 원칙: 이용 조건이 불명확하거나 확인되지 않은 공급처는 **운영 환경에서 기본 비활성화**한다
> (`license_verified=False` → `APP_ENV=production`에서 자동 차단,
> `ALLOW_UNVERIFIED_SOURCES=1`로만 강제 가능). 무료 이용과 상업적 이용은 구분한다.

## 구현 완료 공급처

| 공급처 | 수집기 | 상업적 이용 | 저장·가공·AI 분석 | 출처 표시 | 호출 제한 | 검증 | 공식 문서 |
|---|---|---|---|---|---|---|---|
| 한국수출입은행 환율 (EXIM) | `exim_fx` | ✅ 공공누리 제1유형(공공데이터포털 오픈API) | ✅ 허용 | 필수 | 신청 단위 일 1,000건(기본, 상향 신청 가능) | ✅ | data.go.kr 공공데이터포털 '한국수출입은행_현재환율API' |
| 한국은행 ECOS | `ecos_rate` | ✅ 공공누리 제1유형 | ✅ 허용 | 필수 | 인증키당 일 10,000건 | ✅ | ecos.bok.or.kr 오픈API 안내 |
| GDELT DOC 2.0 | `gdelt` | ✅ 자유 이용(저작권자가 제한 완화 명시) | ✅ 허용(수집·분석·게시 모두 명시적 허용) | 권장("GDELT Project" 표기) | **요청 간 5초 이상 간격 필수** | ✅ | gdeltproject.org/about.html#termsofuse |
| FRED (연준 경제데이터) | `fred` | ✅ 출처 표기 조건으로 허용 | ✅ 허용 | 필수 | 분당 ~120건(가이드라인) | ✅ | fred.stlouisfed.org/docs/api/terms_of_use.html |
| EIA (미 에너지정보청) | `eia` | ✅ 미국 정부 공공데이터 | ✅ 허용 | 필수 | 시간당 ~1,000건 | ✅ | eia.gov/about/copyrights_reuse.php |
| OpenDART | `dart` | ✅ 공공데이터포털 오픈API(공공누리) | ✅ 허용 | 필수 | 일 10,000건(오픈API 한도) | ✅ | opendart.fss.or.kr 오픈API 이용안내 |
| Google 뉴스 RSS | `news_rss` | ❌ **불명확** — RSS 제공이 상업적 이용 허용을 의미하지 않음 | ⚠️ 제목·링크·메타만 저장, 원문 전재 금지 원칙 | 기사 원 출처 표기 | 비공식 | ❌ **미검증 → 운영 기본 비활성** | news.google.com (이용 조건 문서 부재) |

### news_rss(Google 뉴스) 처리 방침
- 개발 환경에서는 동작하나 `APP_ENV=production`이면 `ALLOW_UNVERIFIED_SOURCES` 없이 실행되지 않는다.
- 정식 운영 시에는 허용 조건이 명확한 언론사 RSS 또는 유료 뉴스 API로 교체하는 것을 권장한다.
- 저장 범위를 제목·요약(피드 제공분)·링크·발행시각·출처로 제한하며, 기사 원문 크롤링은 하지 않는다.

## 미구현 공급처 (지시서 목록 대비 — 제한 사유 기록)

| 공급처 | 상태 | 사유 |
|---|---|---|
| 관세청 수출입무역통계 | 미구현 | 공공데이터포털 API(품목별 수출입 실적) 존재 — 키 발급 후 구현 가능. 반도체 수출입 통계 확보 시 우선순위 높음 |
| KOSIS (통계청) | 미구현 | KOSIS 오픈API 존재(무료 키) — 제조업 생산지표(광공업생산지수) 대상. 키 발급 후 구현 가능 |
| 정부 공식 보도자료 | 미구현 | 부처별 RSS가 없어 GDELT/언론사 피드로 대체 중 — 허용 조건 확인 후 추가 예정 |

## 외부 AI(LLM) 서비스 이용 조건
- 외부 LLM에 기업 데이터를 보내는 것은 **기업별 옵트인**(`companies.allow_external_ai`)이 있을 때만 허용한다.
- 데이터 보존·모델 학습 이용 조건이 확인되지 않은 LLM 공급처에는 실제 기업 기밀을 전송하지 않는다 — 기본은 규칙 기반 엔진.
- 공급처별 비용·이용 조건은 `docs/REQUIRED_API_KEYS.md`에 계속 기록한다.

## 운영 적용 메커니즘
- 각 수집기는 `license_verified` 속성을 가진다 (기본 True).
- `services/collectors/collector_active()`: `enabled(키/설정)` AND (`license_verified` OR `not IS_PROD` OR `ALLOW_UNVERIFIED_SOURCES`).
- `GET /api/collection/status` 응답에 `configured`/`license_verified` 필드로 구분 표시된다.
