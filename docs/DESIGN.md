# dayribbon BI 데모 — 설계 문서

## 설계 결정과 이유

### 1. 백엔드: FastAPI + SQLAlchemy + SQLite
- 지시서 스택 준수. SQLite는 파일 기반이라 데모 배포·재현이 간단.
- 정식 개발 시 TiDB 전환을 대비해 ORM 계층을 분리하고 비즈니스 로직은
  `app/services/`에 모아 DB 비의존적으로 작성했다.

### 2. 인증: DB 토큰 방식
- JWT 라이브러리 없이 `secrets.token_urlsafe` 기반 opaque 토큰을 `auth_tokens`
  테이블에 저장. 데모 규모에서 충분하고 만료·폐기 관리가 단순하다.
- 비밀번호는 PBKDF2(120k iterations, stdlib)로 해시.

### 3. 권한: 역할 상수 + 의존성 주입
- `deps.py`의 `get_current_user`/`require_write`/`require_admin`으로
  모든 쓰기 API에서 백엔드 강제 검증. VIEWER는 403 확인됨.

### 4. 분석 엔진: 규칙 기반 (`services/analysis_engine.py`)
- LLM 미연결 상태에서 투명한 규칙 기반으로 구현.
- 모든 결과에 `engine="rule-based-demo"`, `DEMO_DISCLAIMER`, 사용 데이터,
  수치, 불확실성/가정을 포함 — "AI가 분석했다"고 허위 표시하지 않음.
- 향후 LLM 교체 시 `compute_kpis`/`run_analyses` 인터페이스 유지.

### 5. 위험 감지: 임계값 + 중복 방지
- 환율/이익률/매출/원자재비/고객집중도/부정뉴스 6개 규칙.
- 동일 제목 미해결 알림은 7일 내 중복 생성 차단 → 스케줄러 반복 실행 안전.
- 등급 기준(정상/관심/주의/위험/심각)을 API 응답과 화면에 함께 표시.

### 6. 자동 분석: 이벤트 + 경량 스케줄러
- 트리거: 업로드, 데모 이벤트, 수동 실행, 스케줄러(기본 120초).
- 스케줄러는 위험 감지를 매 주기 실행하고, 분석 결과는 24시간 주기로만
  재생성해 알림 범람을 방지. Airflow 대신 threading 스케줄러 채택(지시서 허용).

### 7. 시뮬레이션: 순수 계산
- 변수 → 영업이익 영향 환산. 변동비율은 최근 12개월 원자재비+인건비 50%로
  근사하고 가정을 결과에 명시. 등급은 영업이익 대비 영향 비율 기준.

### 8. 보고서: 콘텐츠 빌더 + fpdf2
- `build_report_content`가 실제 DB 데이터를 집계해 JSON으로 저장 →
  PDF는 fpdf2 + 맑은 고딕(TTF)으로 한글 출력. Windows 폰트 없으면
  PDF 생성 실패 시 `pdf_path` 비워두고 재생성 가능.

### 9. 프론트엔드: React + Vite + Tailwind v4 + Recharts
- B2B SaaS 톤: 딥 블루 브랜드 + slate 뉴트럴, 좌측 사이드바.
- 카드 나열형 관리자 템플릿을 지양하고 KPI 스트립 → 차트 → 리스트의
  시각적 위계로 구성. 위험은 색상+등급 텍스트+기준 설명 병기.

## 알려진 한계

- 시계열/뉴스/금융 데이터는 시드 생성값이며 실제 API 연동 없음.
- 업로드는 CSV/XLSX만 지원 (PDF OCR 미구현 — 명시됨).
- 이메일/카카오 발송은 "발송 대기" 큐만 구현.
- 멀티테넌트 UI는 없으나 모든 쿼리가 company_id 스코핑.
