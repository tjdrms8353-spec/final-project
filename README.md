# Final Project

## 역할

| 담당 | 역할 | 기술 |
| --- | --- | --- |
| 프런트엔드 1명 | 전체 화면, 대시보드, API 연결 | React, Tailwind, Recharts |
| 성근 | 뉴스·SNS 수집, AI 문서 분류, TOP 10, ETL | Python, FastAPI, Airflow, Polars, Scikit-learn |
| 종범 | 주식·코인 수집 및 분석 | Python, FastAPI, Pandas, 금융 API |
| 승호 | 영수증 OCR 및 자동 등록 | Python, FastAPI, OCR, Playwright |
| 공동 | DB, API 통합, 테스트, 배포 | TiDB, SQL, GitHub, Render, EC2 |

## 실행

프런트엔드: frontend 폴더에서 npm install 후 npm run dev.
PowerShell에서 npm.ps1 실행이 차단되면 npm.cmd install / npm.cmd run dev 사용.

백엔드(Python 설치 필요): backend 폴더에서 다음 실행.

    python -m venv .venv
    .venv\Scripts\activate
    pip install -r requirements.txt
    uvicorn app.main:app --reload --port 8001

Docker 백엔드: docker compose up --build
API 문서: http://127.0.0.1:8001/docs

## 구조와 구현 범위

- frontend/: React 시작점 및 기존 화면(public/legacy)
- backend/app/features/: trends(성근), finance(종범), receipts(승호)
- backend/app/core, db, models, schemas: 공통 설정·DB·모델·스키마
- pipelines/: Airflow DAG, ETL 작업, 테스트(별도 Python 환경)
- models/, data/: 로컬 모델·데이터 저장 위치
- migrations/: Alembic 초기화 및 DB 변경 파일을 추가할 위치
- docs/: planning, design, implementation, deployment
- .github/workflows/: 프런트엔드 빌드 및 Python 구문 검사 CI

백엔드는 health와 각 기능의 status API만 제공합니다. 수집·분석·OCR·TiDB 연결·Airflow DAG·배포는 아직 구현되지 않았습니다. .env.example은 DB 설정 예시이며 TiDB TLS 연결은 db에서 구현해야 합니다.

기존 HTML과 자산은 상대 경로를 유지한 채 frontend/public/legacy로 옮겼습니다. React의 대시보드 페이지는 iframe으로 기존 화면을 표시합니다. React로 완전히 변환된 상태는 아닙니다. 트렌드·금융·문서 AI·영수증 OCR·운영 콘솔은 Google AI Studio의 데모 화면으로 통합했습니다. 대시보드는 기존 화면을 유지하며 기존 업로드 화면도 하단 링크에서 이용할 수 있습니다.
기존 프런트엔드 문서는 docs/implementation/legacy-frontend.md에 있습니다.
