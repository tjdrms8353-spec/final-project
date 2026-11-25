import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# TiDB/MySQL 전환 시: mysql+pymysql://user:pass@host:4000/dayribbon
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR / 'dayribbon.db'}")

TOKEN_TTL_HOURS = int(os.getenv("TOKEN_TTL_HOURS", str(24 * 7)))

CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")

# 자동 분석 주기(초). 데모에서는 짧게 설정해 동작을 확인할 수 있게 한다.
AUTO_ANALYSIS_INTERVAL_SEC = int(os.getenv("AUTO_ANALYSIS_INTERVAL_SEC", "120"))

SEED_DEMO = os.getenv("SEED_DEMO", "1") == "1"

# 데모 전용 라우터 노출 여부. 실서비스에서는 반드시 0 (실데이터 오염 방지)
DEMO_EVENTS_ENABLED = os.getenv("DEMO_EVENTS_ENABLED", "1") == "1"

# --- LLM 분석 모듈 (미연결 시 규칙 기반 엔진으로 폴백) ---
# 지원: 호환 OpenAI API 엔드포인트 (예: Ollama, OpenRouter, vLLM)
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")  # 예: http://localhost:11434/v1
LLM_MODEL = os.getenv("LLM_MODEL", "")

# --- 외부 데이터 수집 API 키 (미연결, 인터페이스만 정의) ---
EXIM_API_KEY = os.getenv("EXIM_API_KEY", "")      # 한국수출입은행 환율 API
ECOS_API_KEY = os.getenv("ECOS_API_KEY", "")      # 한국은행 ECOS
DART_API_KEY = os.getenv("DART_API_KEY", "")      # DART 전자공시
NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")      # 뉴스 수집용
