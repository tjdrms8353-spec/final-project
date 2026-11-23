import ssl
from functools import lru_cache

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings


def get_database_url() -> URL:
    settings = get_settings()
    if not all((settings.tidb_host, settings.tidb_user, settings.tidb_database)):
        raise RuntimeError("Set TIDB_HOST, TIDB_USER and TIDB_DATABASE before using the database.")
    return URL.create(
        "mysql+pymysql",
        username=settings.tidb_user,
        password=settings.tidb_password.get_secret_value(),
        host=settings.tidb_host,
        port=settings.tidb_port,
        database=settings.tidb_database,
        query={"charset": "utf8mb4"},
    )


@lru_cache
def get_engine():
    settings = get_settings()
    url = get_database_url()
    tls = ssl.create_default_context(cafile=settings.tidb_ssl_ca or None)
    return create_engine(
        url, pool_pre_ping=True,
        connect_args={"ssl": tls, "connect_timeout": 10},
    )


def get_db():
    with Session(get_engine()) as session:
        yield session
