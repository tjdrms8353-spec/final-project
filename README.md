# dayribbon BI Demo

AI 기반 중소기업형 맞춤형 BI 시스템 — **독립 데모 프로젝트**

기존 프로젝트와 무관한 신규 개발 데모입니다. 모든 기업·시장 데이터는 가상이며,
분석은 **규칙 기반 데모 엔진**(실제 LLM 아님)이 수행합니다.

## 기술 스택

- **Frontend**: React 18 + Vite + Tailwind CSS v4 + Recharts + React Router
- **Backend**: Python FastAPI + SQLAlchemy + Pydantic + SQLite
- **데이터 처리**: Pandas (Excel/CSV 업로드), fpdf2 (한글 PDF 보고서)

## 실행 방법 (Windows)

```powershell
# 1) 최초 1회 설치
.\setup.ps1

# 2) 실행 (백엔드+프론트엔드 동시)
.\start.ps1
```

Linux/macOS:

```bash
chmod +x setup.sh start.sh stop.sh
./setup.sh
./start.sh
```

포트가 사용 중이면 자동으로 다음 사용 가능한 포트를 선택합니다.
실행 후 출력되는 주소로 접속하세요.

## 접속 주소 (기본값)

| 항목 | 주소 |
|---|---|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs (Swagger) | http://localhost:8000/docs |

## 데모 로그인

비밀번호는 모두 `demo1234` 입니다.

| 권한 | 이메일 | 설명 |
|---|---|---|
| OWNER | owner@dayribbon.demo | 기업 대표 — 전체 권한 |
| ADMIN | admin@dayribbon.demo | 관리자 — 분석 검토·의사결정 권한 |
| MEMBER | member@dayribbon.demo | 실무 — 데이터 등록·수정 권한 |
| VIEWER | viewer@dayribbon.demo | 읽기 전용 — 외부 감사 역할 (수정 API 403 차단) |

## 데모 데이터

- 가상 기업: **(데모) 한빛세미텍** — 반도체 부품 제조업
- 최근 24개월 매출/영업이익/비용, 제품별·거래처별 실적, 원자재 구매
- 환율·금리·주가지수·원자재가 24개월 시계열
- 산업 뉴스 18건 (모두 가상)
- 첫 실행 시 자동 시드 (`SEED_DEMO=1`). DB는 `backend/data/dayribbon.db`

## 데모 이벤트 (알림 센터 메뉴)

테스트용 시장 변동 재현 버튼입니다. 실제 금융 데이터가 아니며,
실행 시 데이터 등록 → 분석 → 위험 판단 → 알림 → 대시보드 갱신이 실제로 수행됩니다.

## 핵심 기능

- 통합 경영 대시보드 (KPI·차트·위험 현황)
- 뉴스/산업 동향 (기업 관련성 점수 기반 선별)
- 금융·경제 지표 (기업 영향 설명 포함)
- 내부 데이터 관리 (Excel/CSV 업로드, 검증, 이력)
- AI 경영 분석 (성장/방향성/위험 — 규칙 기반, 근거·불확실성 명시)
- 위험 영향 시뮬레이션 (환율/금리/원자재/매출 변동)
- 자동 분석·모니터링 (업로드·이벤트·주기적 위험 감지)
- 알림 센터 (위험/뉴스/KPI/이메일 발송 대기)
- 의사결정·후속 조치 관리 (사람이 최종 결정)
- 월간 경영 보고서 + PDF 다운로드 (한글 지원)
- 감사 추적 로그 (읽기 전용)
- 역할 기반 권한 (백엔드 API 레벨 강제)

## 프로젝트 구조

```
dayribbon-bi-demo/
├── frontend/          # React + Vite SPA
│   └── src/pages/     # 화면별 페이지
├── backend/
│   ├── app/
│   │   ├── routers/   # API 라우터 (기능별 분리)
│   │   ├── services/  # 분석엔진/시뮬레이션/보고서 생성
│   │   ├── models.py  # SQLAlchemy 모델 (TiDB 이전 대비 분리 설계)
│   │   └── seed.py    # 데모 데이터 생성
│   └── run.py
├── sample-data/       # 업로드 테스트용 CSV
├── docs/              # 설계 문서
├── setup.ps1 / start.ps1 / stop.ps1
├── setup.sh / start.sh / stop.sh
└── .env.example
```

## 환경 변수

`.env.example` 참고. 주요 항목: `DATABASE_URL`, `SECRET_KEY`, `SEED_DEMO`,
`AUTO_ANALYSIS_INTERVAL_SEC`, `CORS_ORIGINS`, `VITE_BACKEND_URL`.

## 제한 사항 (데모)

- 분석은 규칙 기반이며 LLM을 사용하지 않습니다 (화면에 "데모 분석" 명시).
- 뉴스·금융 데이터는 실제 API가 아닌 데모 생성 데이터입니다.
- 이메일/카카오 알림은 실제 발송되지 않고 "발송 대기"로 기록됩니다.
- PDF 재무제표 OCR 및 ERP 연동은 미구현입니다.
- 단일 데모 테넌트만 시드되지만 모든 조회는 `company_id`로 스코핑됩니다.
