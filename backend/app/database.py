from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import (
    DATABASE_URL, DB_POOL_RECYCLE, DB_POOL_SIZE, DB_SSL_CA, DB_SSL_REQUIRED,
)

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_mysql = DATABASE_URL.startswith(("mysql", "mariadb"))

if _is_sqlite:
    connect_args = {"check_same_thread": False}
    pool_kwargs = {}
else:
    # TiDB/MySQL — TLS CA 파일 또는 시스템 CA로 SSL 연결 (pymysql 형식)
    if _is_mysql and DB_SSL_CA:
        connect_args = {"ssl": {"ca": DB_SSL_CA}}
    elif _is_mysql and DB_SSL_REQUIRED:
        connect_args = {"ssl": {"ca": None}}  # 시스템 CA 사용 (TiDB Serverless 등)
    else:
        connect_args = {}
    pool_kwargs = {
        "pool_size": DB_POOL_SIZE,
        "pool_recycle": DB_POOL_RECYCLE,  # 유휴 커넥션 재활용
        "pool_pre_ping": True,            # 끊긴 커넥션 자동 감지
    }

engine = create_engine(DATABASE_URL, connect_args=connect_args,
                       future=True, **pool_kwargs)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_db() -> dict:
    """DB 연결 상태 확인. 헬스체크 API에서 사용."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"ok": True, "dialect": engine.dialect.name}
    except Exception as e:
        return {"ok": False, "dialect": engine.dialect.name, "error": str(e)}
