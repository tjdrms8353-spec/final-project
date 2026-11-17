# 통합 프런트엔드

## 실행

    npm install
    npm run dev
    npm run typecheck
    npm run build

PowerShell에서 npm.ps1이 차단되면 npm.cmd를 사용하세요.

## 통합 구성

Google AI Studio의 React/TypeScript 화면을 기존 React/Vite 앱에 통합했습니다.
- src/pages/DashboardPage.jsx: 기존 AutoFlow 대시보드(iframe)
- src/pages/TrendPage.jsx: 뉴스·SNS 분석
- src/pages/FinancePage.jsx: 금융 분석
- src/pages/ReceiptPage.jsx: 영수증 OCR 데모
- src/pages/DocumentPage.jsx: AI 문서 분류 데모
- src/pages/DataOpsPage.jsx: 운영 콘솔
- src/components/: AI Studio 화면 및 공통 UI, 기존 LegacyPage
- src/context/PlatformContext.tsx: 공유 데모 상태와 역할 시뮬레이션
- src/data/mockDb.ts: 샘플 데이터와 번들 이미지 참조
- src/types/: TypeScript 모델
- src/services/api.js: 기존 API 호출 진입점(보존)
- public/legacy/: 기존 AutoFlow HTML/CSS/JavaScript 원본

메인 화면은 뉴스·SNS 탭으로 시작합니다. 상단 대시보드 탭과 하단 링크에서 기존 화면에 접근할 수 있습니다.
기존 로그인 및 문서 처리 상태와 새 플랫폼 데모 상태는 별개입니다.

## API 상태

가져온 화면은 브라우저 메모리 기반 데모입니다. 로그인/OAuth, 문서 분류, OCR, RPA, Airflow, TiDB 저장은 실제 API 호출이 아닙니다. 새로고침하면 데모 변경 내역이 초기화됩니다. Gemini API 키는 필요하지 않으며 클라이언트에 포함하지 않습니다.
기존 /api → http://127.0.0.1:8001 개발 프록시와 VITE_API_BASE_URL 설정을 유지했습니다. 백엔드 업무 API 구현 후 services와 PlatformContext를 연결하세요.
이미지는 Vite import로 묶어 개발·배포 환경에서 동일하게 표시합니다.
