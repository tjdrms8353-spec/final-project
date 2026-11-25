from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import (
    DATABASE_URL, DB_POOL_RECYCLE, DB_POOL_SIZE, DB_SSL_CA,
)

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    connect_args = {"check_same_thread": False}
    pool_kwargs = {}
else:
    # TiDB/MySQL — TLS CA 지정 시 SSL 연결
    connect_args = {"ssl": {"ca": DB_SSL_CA}} if DB_SSL_CA else {}
    pool_kwargs = {
        "pool_size": DB_POOL_SIZE,
        "pool_recycle": DB_POOL_RECYCLE,  # TiDB 유휴 커넥션 재활용
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
