import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# 프로젝트 루트 .env 로드 — 없으면 무시. 이미 설정된 환경변수가 우선한다.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR.parent / ".env")
except ImportError:
    pass

# 실행 환경: dev(기본) / production
APP_ENV = os.getenv("APP_ENV", "dev")
IS_PROD = APP_ENV == "production"

# TiDB/MySQL 전환 시: mysql+pymysql://user:pass@host:4000/dayribbon
# Render 등 PaaS PostgreSQL: postgres:// 접두어를 SQLAlchemy 형식으로 정규화
_db_url = os.getenv("DATABASE_URL")
if _db_url and _db_url.startswith("postgres://"):
    _db_url = "postgresql://" + _db_url[len("postgres://"):]
if IS_PROD and (not _db_url or _db_url.startswith("sqlite")):
    raise RuntimeError(
        "[dayribbon] 운영 환경(APP_ENV=production)에는 DATABASE_URL에 "
        "외부 DB 접속 정보(mysql+pymysql:// 또는 postgresql://)가 필요합니다. "
        "SQLite·기본값으로는 운영 환경을 시작할 수 없습니다.")
DATABASE_URL = _db_url or f"sqlite:///{DATA_DIR / 'dayribbon.db'}"

# TiDB Cloud TLS CA 경로 (mysql 계열 접속 시 사용)
DB_SSL_CA = os.getenv("DB_SSL_CA", "")
# CA 파일 없이 시스템 CA로 TLS 강제 (TiDB Serverless 등 TLS 필수 접속용)
DB_SSL_REQUIRED = os.getenv("DB_SSL_REQUIRED", "0") == "1"

# 커넥션 풀 (sqlite에는 pool_size 미적용)
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "300"))

TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", str(24 * 7)))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# 자동 분석 주기(초). 데모에서는 짧게 설정해 동작을 확인할 수 있게 한다.
AUTO_ANALYSIS_INTERVAL_SEC = int(os.getenv("AUTO_ANALYSIS_INTERVAL_SEC", "120"))

# 운영 환경에서는 데모 데이터 시드·데모 이벤트 기본 비활성
_seed_default = "0" if IS_PROD else "1"
SEED_DEMO = os.getenv("SEED_DEMO", _seed_default) == "1" and not IS_PROD

# 데모 전용 라우터 노출 여부. 실서비스에서는 반드시 0 (실데이터 오염 방지)
DEMO_EVENTS_ENABLED = os.getenv("DEMO_EVENTS_ENABLED", _seed_default) == "1" and not IS_PROD

# --- LLM 분석 모듈 (미연결 시 규칙 기반 엔진으로 폴백) ---
# 지원: 호환 OpenAI API 엔드포인트 (예: Ollama, OpenRouter, vLLM)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")  # 예: http://localhost:11434/v1
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_TIMEOUT_SEC = int(os.getenv("LLM_TIMEOUT_SEC", "30"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "1"))
# 월간 LLM 토큰 예산 — 0이면 제한 없음. 초과 시 자동으로 규칙 엔진 폴백
LLM_MONTHLY_TOKEN_BUDGET = int(os.getenv("LLM_MONTHLY_TOKEN_BUDGET", "0"))

# --- 외부 데이터 수집 (정식 전환 B) ---
EXIM_API_KEY = os.getenv("EXIM_API_KEY", "")      # 한국수출입은행 환율 API
ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")      # 한국은행 ECOS
DART_API_KEY = os.getenv("DART_API_KEY", "")      # DART 전자공시 (미구현)
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")      # 뉴스 검색 API (RSS 수집에는 불필요)

# 수집 주기·타임아웃
COLLECT_INTERVAL_SEC = int(os.getenv("COLLECT_INTERVAL_SEC", str(6 * 3600)))
COLLECT_TIMEOUT_SEC = int(os.getenv("COLLECT_TIMEOUT_SEC", "15"))

# 뉴스 RSS 수집 — API 키 없이 동작. 쉼표로 여러 피드 지정 가능.
# 참고: Google 뉴스 RSS는 상업적 이용 조건이 불명확 — 운영 환경에서는
# ALLOW_UNVERIFIED_SOURCES=1 또는 허용이 확인된 피드로 교체 전까지 기본 비활성.
NEWS_COLLECT_ENABLED = os.getenv("NEWS_COLLECT_ENABLED", "1") == "1"
NEWS_RSS_URLS = os.getenv(
    "NEWS_RSS_URLS",
    "https://news.google.com/rss/search?"
    "q=%ED%99%98%EC%9C%A8+OR+%EC%88%98%EC%B6%9C%EC%9E%85+OR+%EC%9B%90%EC%9E%90%EC%9E%AC"
    "&hl=ko&gl=KR&ceid=KR:ko",
)

# GDELT — 오픈 데이터(저작권 제한 완화, 출처 표기 권장). 키 불필요.
GDELT_ENABLED = os.getenv("GDELT_ENABLED", "1") == "1"

# 미국 공공 데이터 (무료 키 발급, 공공데이터 성격)
FRED_API_KEY = os.getenv("FRED_API_KEY", "")      # FRED (연준 경제데이터)
EIA_API_KEY = os.getenv("EIA_API_KEY", "")        # EIA (에너지 가격)

# OpenDART — 기업 공시 (무료 키 발급). 수집 대상 corp_code 목록(쉼표 구분)
DART_CORP_CODES = os.getenv("DART_CORP_CODES", "")

# 운영 환경에서 이용 조건 미검증 공급처를 강제 활성화할 때만 1로 설정
ALLOW_UNVERIFIED_SOURCES = os.getenv("ALLOW_UNVERIFIED_SOURCES", "0") == "1"

# --- 알림 실발송 (정식 전환 D) ---
# SMTP 이메일 — 미설정 시 발송 큐가 '설정 대기'로 남고 설정 후 자동 발송
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "")           # 비워두면 SMTP_USER 사용
SMTP_STARTTLS = os.getenv("SMTP_STARTTLS", "1") == "1"

# 카카오 알림톡 — 벤더 API(알리고/비즈톡 등) 키 필요. 미설정 시 비활성
KAKAO_API_URL = os.getenv("KAKAO_API_URL", "")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY", "")
KAKAO_SENDER_KEY = os.getenv("KAKAO_SENDER_KEY", "")

# 발송 워커 — 스케줄러 tick마다 처리. 재시도 상한 초과 시 failed
DELIVERY_MAX_ATTEMPTS = int(os.getenv("DELIVERY_MAX_ATTEMPTS", "3"))
