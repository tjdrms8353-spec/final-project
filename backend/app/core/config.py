from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "dayribbon"
    cors_origins: list[str] = ["http://localhost:5175"]
    tidb_host: str = ""
    tidb_port: int = 4000
    tidb_user: str = ""
    tidb_password: SecretStr = SecretStr("")
    tidb_database: str = ""
    tidb_ssl_ca: str = ""
    # Optional. Empty disables translation jobs.
    deepl_api_key: SecretStr = SecretStr("")
    # Optional local/dev override, e.g. sqlite:///data/dayribbon.db. Empty uses TiDB settings.
    database_url: str = ""
    # Signs dayribbon BI login tokens. Must be set to a long random value in production.
    auth_secret: SecretStr = SecretStr("")
    auth_token_hours: int = 12
    # Optional LLM for narrating verified analysis numbers (OpenAI-compatible Chat Completions).
    llm_api_key: SecretStr = SecretStr("")
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"


@lru_cache
def get_settings() -> Settings:
    return Settings()
