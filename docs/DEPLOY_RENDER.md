# Render 배포 가이드 (DEPLOY_RENDER)

작성일: 2026-11-26

## 구성

- `dayribbon-api` — FastAPI 백엔드 (Docker Web Service)
- `dayribbon-web` — React 정적 사이트 (Static Site)
- DB — **TiDB Cloud Serverless** (Render는 MySQL 미제공 — 외부 접속)

`render.yaml` 블루프린트가 두 서비스를 자동 생성한다.

## 사전 준비

1. **코드를 GitHub에 push** — Render는 저장소에서 `render.yaml`을 읽는다.
2. **Render 계정** — https://render.com (GitHub 로그인 가능)
3. **TiDB Cloud Serverless 클러스터** — https://tidbcloud.com 무료 생성
   - 클러스터 생성 후 `Connect` → 접속 정보 확인
   - 접속 문자열 형식: `mysql+pymysql://<user>:<password>@<host>:4000/<db명>`
   - TiDB Serverless는 TLS 필수 — `DB_SSL_REQUIRED=1`이 블루프린트에 포함됨
   - 대상 데이터베이스가 없으면 클러스터에서 `CREATE DATABASE dayribbon;` 실행

## 배포 절차

1. Render Dashboard → **New → Blueprint**
2. GitHub 저장소 연결 → 이 저장소·배포할 브랜치 선택
3. `render.yaml`이 인식되면 서비스 목록 확인 → **Apply**
4. `sync: false`로 표시된 `DATABASE_URL`에 TiDB 접속 문자열 입력
5. 두 서비스 배포 완료 후 확인:
   - `https://dayribbon-api.onrender.com/api/health` → `{"status":"ok"}` 계열 응답
   - `https://dayribbon-api.onrender.com/api/health/db` → `{"ok":true,"dialect":"mysql"}`
   - `https://dayribbon-web.onrender.com` → 회원가입 → 기업 등록 → 온보딩

## 주의 사항

- 최초 기동 시 `create_all`로 전체 테이블이 생성된다 (신규 DB 기준).
- `CORS_ORIGINS`는 프론트 도메인(`dayribbon-web.onrender.com`)으로 설정됨 —
  서비스 이름을 바꾸면 두 env를 함께 수정해야 한다.
- 무료 플랜: 일정 시간 요청이 없으면 슬립(첫 요청 시 깨어나며 수십 초 지연),
  월 사용량 제한 있음 — 최신 조건은 Render 요금제 문서 확인.
- LLM·수집기 API 키(EXIM/ECOS/FRED/EIA/DART)는 배포 후
  대시보드 → dayribbon-api → Environment에서 추가하면 된다.
- 데모 시드·데모 이벤트는 `APP_ENV=production`에서 자동 비활성 — 시연용
  데이터가 필요하면 별도 회원가입/데이터 입력으로 만든다.
- Google 뉴스 RSS는 운영 기본 비활성(이용 조건 미검증) — GDELT 수집기가 동작한다.
