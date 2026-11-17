# AutoFlow 프런트엔드 구현 가이드

이 문서는 저장소의 현재 `README.md`(프로젝트명 `Finalproject`)와 요청에 명시된 AutoFlow 요구사항을 기준으로 한 프런트엔드 착수안입니다. 기존 README에는 제목 외 별도 구조나 규칙이 없어, 아래 설계는 요청 내용을 기준으로 구성했습니다.

## 제품 목표와 팀 경계

AutoFlow는 PDF 영수증·세금계산서·이메일을 수집해 OCR+LLM으로 구조화하고, 검토를 거쳐 ERP/엑셀에 자동 입력하는 B2B SaaS입니다. 사용자 여정은 **현황 확인 → 문서 등록/검토 → 이력 조회 → RPA 실행 모니터링 → 계정/연동 설정**입니다.

| 백엔드 범주 | 담당 | 프런트에서 기대하는 책임 |
| --- | --- | --- |
| 인증·사용자·공통 API | 안종범 | 로그인/권한, 사용자·조직 설정, 공통 문서 조회 API, API 인증 |
| 문서 AI 파이프라인 | 송성근 | 파일 수집, OCR/LLM 작업 상태, 추출 필드·신뢰도, 검토/승인 저장 |
| RPA·ERP·스케줄러 | 이승호 | 봇 상태/대기열/로그, 실행·중지, ERP 연동, 리포트 내보내기 |

황상옥 담당 프런트엔드는 화면, 폼 검증, API 어댑터, 로딩/오류/빈 상태를 제공합니다. 각 백엔드 프로젝트를 `auth-core`, `document-ai`, `rpa-bridge`로 가정해 명세를 나눴습니다. 실제 서비스 URL과 인증 방식은 백엔드 팀과 합의 후 `frontend/assets/js/api.js`의 설정값을 변경하세요.

## 페이지 아웃라인

| 화면 | 파일 | 핵심 동작 |
| --- | --- | --- |
| 대시보드/랜딩 | `index.html` | KPI, 최근 문서, 처리 추이, 세 백엔드 범주 바로가기 |
| 문서 업로드·검토 | `upload.html` | PDF/이미지/EML 업로드, 원본 미리보기, 추출 값 편집, 승인/엑셀 다운로드 |
| 데이터 이력 | `history.html` | 날짜·유형·상태·거래처 검색, 테이블, 거래처 비용 추이 |
| RPA 모니터링 | `admin_rpa.html` | 봇 상태/큐, 로그, 수동 실행, 일일 리포트 |
| 설정·계정 | `preferences.html` | 프로필/권한, 알림, ERP 연결 상태 |
| 인증 | `login.html` | 로그인 및 시연용 데모 진입 |
| 시연 데이터 | `samples.html` | 가상 영수증·세금계산서·이메일 샘플을 선택해 업로드/검토 흐름 실행 |

요청의 핵심 6개 화면은 유지하고, 면접 시연을 돕는 `samples.html`을 공통 헤더에서 접근 가능한 보조 페이지로 추가했습니다. 로그인과 회원가입은 `login.html`의 탭으로 묶었습니다. 실제 회원가입 정책이 없는 사내 서비스라면 가입 탭을 비활성/초대 안내로 바꾸세요.

## 디렉터리 구조

```text
frontend/
  README.md
  index.html
  upload.html
  history.html
  admin_rpa.html
  preferences.html
  login.html
  samples.html
  assets/
    css/app.css
    css/theme.css
    css/dashboard.css
    dashboard-automation.svg
    dashboard-horizon.svg
    js/api.js       # 세 백엔드 API 어댑터 및 mock fallback
    js/app.js       # 공통 내비게이션, 사용자 메뉴, 날짜, 맨 위 버튼
    js/dashboard.js
    js/upload.js
    js/history.js
    js/rpa.js
    js/preferences.js
    js/auth.js
    js/samples.js
```

`시연 데이터`는 화면 렌더링용 가상 문서를 `sessionStorage`로 업로드 화면에 전달합니다. 샘플 문서 승인 버튼은 데모 완료 메시지만 보여주며 실제 ERP/RPA API를 호출하지 않습니다. 발표 중 실제 문서 업로드와 샘플 시연을 혼동하지 않도록 각 샘플과 업로드 원본에 데모 표시를 노출합니다. 기본 색상은 웜 뉴트럴, 세이지, 브론즈로 제한하고, 대시보드의 벡터 아트도 같은 색조로 맞춥니다.

대시보드의 프로세스 레인은 최근 문서 정보를 사용해 수집 → AI 분석 → 검증 → RPA → 완료 순서를 반복 시각화합니다. 현재는 화면 시연용 프리뷰이며, 실제 진행 상태 연동은 `GET /api/v1/rpa/runs/{runId}` 또는 SSE 로그 이벤트 계약을 백엔드와 합의한 뒤 단계 값을 구독하도록 교체합니다. 사용자가 OS의 동작 줄이기 설정을 선택한 경우 자동 애니메이션을 정지합니다.

## 공통 UI/UX 규칙

- 화면은 Bootstrap 5.3 기반, 데스크톱 우선이지만 768px 이하에서는 카드와 split view를 한 열로 재배치합니다. Bootstrap Icons와 Plotly는 CDN을 사용합니다.
- 고정 헤더 높이 68px, 본문은 `#app-main`에 상단 여백을 줍니다. 사이드바 대신 상단 메뉴와 페이지 내 섹션 앵커를 사용해 작은 화면에서도 탐색을 단순화합니다.
- 색상은 잉크 네이비 `#101828`, 바이올렛 `#6857E8`, 시안 `#42C8C5`, 배경 `#F5F7FB`을 사용합니다. 성공/검토/실패는 색상만으로 표현하지 않고 텍스트 배지와 아이콘을 같이 표시합니다.
- 모든 액션은 로딩·성공·실패 피드백을 표시하고, 폼에는 label과 키보드 포커스 스타일을 제공합니다. 업로드는 파일 형식·크기·중복을 검사하고 서버 검증 오류도 필드 근처에 노출합니다.
- 명시적 실시간 API가 준비되기 전까지 10초 폴링을 기본값으로 두고, 페이지 이탈 시 타이머를 해제합니다. API 실패 시 mock 데이터는 “데모 데이터”로 표시합니다.
- 이모지 대신 단순한 AutoFlow 벡터 마크를 공통 파비콘/브랜드 마크로 사용합니다. 같은 심볼을 헤더와 로그인 화면에서 반복해 브랜드 인지를 강화합니다.

## 실행 방법

정적 페이지이므로 `frontend/`를 Netlify에 배포하거나 로컬 정적 서버로 실행합니다. `file://` 직접 열기는 모듈/CORS 제약 때문에 피하세요. 예: `npx serve frontend`. 각 API 주소는 `api.js`의 `API_BASE` 설정 또는 배포 환경별 설정 파일에서 지정합니다. 정적 호스팅만으로 비밀 API 키를 안전하게 보관할 수 없으므로 ERP 비밀값은 브라우저에 입력/저장하지 않고 백엔드 설정 화면/API에서 관리해야 합니다.

## REST API 인터페이스 초안

공통: JSON은 UTF-8, 시간은 ISO-8601 UTC, 금액은 정수 원 단위, 페이지네이션은 `{items, page, pageSize, total}`. 인증은 `Authorization: Bearer <access_token>` 가정. 오류 응답 `{error:{code,message,fields?}, requestId}`. 프런트는 401에서 로그인으로 이동하고, 403은 권한 안내, 409는 최신 데이터 재조회, 5xx는 재시도 가능한 오류로 처리합니다.

### 1) 인증·사용자·공통 API (`auth-core`)

| Method | Endpoint | 요청/응답 요약 |
| --- | --- | --- |
| POST | `/api/v1/auth/login` | `{email,password}` → `{accessToken,user}` |
| POST | `/api/v1/auth/logout` | 세션 종료 |
| GET | `/api/v1/me` | `{id,name,email,role,organization}` |
| GET | `/api/v1/dashboard/summary?from=&to=` | KPI 및 일별 추이 |
| GET | `/api/v1/documents?from=&to=&type=&status=&vendor=&q=&page=` | 문서 목록/필터 결과 |
| GET | `/api/v1/documents/{id}` | 문서 메타데이터·추출 결과 상세 |
| GET/PATCH | `/api/v1/settings/profile` | 사용자 프로필 조회/수정 |
| GET/PATCH | `/api/v1/settings/notifications` | 이메일/웹훅 알림 설정 |

### 2) 문서 AI (`document-ai`)

| Method | Endpoint | 요청/응답 요약 |
| --- | --- | --- |
| POST | `/api/v1/documents` | multipart `file`, `sourceType` → `{id,status}`; 202 비동기 처리 |
| GET | `/api/v1/documents/{id}/extraction` | `{status,fields:[{key,label,value,confidence}],previewUrl,errors}` |
| PATCH | `/api/v1/documents/{id}/extraction` | 검토자가 수정한 필드와 `version` 저장 |
| POST | `/api/v1/documents/{id}/approve` | `{version,destination}` → ERP 전달/RPA 큐 등록 결과 |
| GET | `/api/v1/documents/{id}/preview` | 원본 미리보기 URL 또는 안전한 텍스트 |
| GET | `/api/v1/reports/vendors?from=&to=&vendorId=` | 거래처별 월 비용 집계 (차트용) |
| GET | `/api/v1/reports/monthly?year=` | 월별 문서/금액 리포트 |
| GET | `/api/v1/documents/{id}/export?format=xlsx` | 엑셀 파일 다운로드 (권한/감사로그 기록) |

### 3) RPA·ERP·스케줄러 (`rpa-bridge`)

| Method | Endpoint | 요청/응답 요약 |
| --- | --- | --- |
| GET | `/api/v1/rpa/bots` | `{items:[{id,name,status,queueCount,lastRunAt}]}` |
| GET | `/api/v1/rpa/logs?since=&level=&botId=&cursor=` | 로그 페이지 또는 SSE 스트림 URL |
| POST | `/api/v1/rpa/bots/{id}/runs` | `{documentIds?,mode}` → `{runId,status}`; 중복 실행 방지 키 권장 |
| POST | `/api/v1/rpa/bots/{id}/stop` | 진행 중 작업 중지 요청 |
| GET | `/api/v1/rpa/runs/{runId}` | 실행 상세/결과 |
| GET | `/api/v1/rpa/integrations` | ERP 연결 상태/표시용 계정명 (비밀값 제외) |
| POST | `/api/v1/rpa/reports/daily?date=` | CSV/XLSX 리포트 다운로드 |

**계약 합의 사항:** 실제 백엔드 포트/경로, role 문자열, 상태 enum(`queued/processing/review/approved/succeeded/failed`), 파일 최대 크기, 저장 기간, SSE 지원, refresh token 방식, 엑셀 응답 헤더를 착수 초기에 확정합니다. 로그와 원본 문서는 민감정보를 포함할 수 있어 화면 접근 권한과 다운로드 감사 정책도 백엔드와 맞춥니다.

## 구현 스켈레톤

아래 페이지는 공통 파일을 불러오는 동작 가능한 정적 UI 초안입니다. `api.js`에서 mock fallback을 제공하며, 실제 API 연결 시 `window.AUTOFLOW_CONFIG.apiBase`를 지정하거나 로컬 설정을 수정합니다. 각 JS 파일은 데이터 연결 지점을 주석과 함수 경계로 분리합니다.
