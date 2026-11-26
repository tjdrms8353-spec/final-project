from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import (
    BASE_DIR, DATABASE_URL, DB_POOL_RECYCLE, DB_POOL_SIZE,
    DB_SSL_CA, DB_SSL_REQUIRED,
)

_is_sqlite = DATABASE_URL.startswith("sqlite")
_is_mysql = DATABASE_URL.startswith(("mysql", "mariadb"))


def _resolve_ca(path: str) -> str | None:
    """CA 경로 해석 — 상대 경로는 프로젝트 루트 기준.
    파일이 없으면 None 반환 → 시스템 CA로 폴백 (TLS 검증은 유지)."""
    if not path:
        return None
    p = Path(path)
    if not p.is_absolute():
        p = BASE_DIR.parent / p
    return str(p) if p.exists() else None


if _is_sqlite:
    connect_args = {"check_same_thread": False}
    pool_kwargs = {}
else:
    # TiDB/MySQL — TLS CA 파일 또는 시스템 CA로 SSL 연결 (pymysql 형식).
    # ca=None 도 TLS 검증 활성(시스템 CA 저장소 사용). 검증 비활성화는 하지 않는다.
    _ca = _resolve_ca(DB_SSL_CA)
    if _is_mysql and _ca:
        connect_args = {"ssl": {"ca": _ca}}
    elif _is_mysql and (DB_SSL_CA or DB_SSL_REQUIRED):
        connect_args = {"ssl": {"ca": None}}  # CA 파일 없음 → 시스템 CA
    else:
        connect_args = {}
    pool_kwargs = {
        "pool_size": DB_POOL_SIZE,
        "pool_recycle": DB_POOL_RECYCLE,  # 유휴 커넥션 재활용
        "pool_pre_ping": True,            # 끊긴 커넥션 자동 감지
    }

engine = create_engine(DATABASE_URL, connect_args=connect_args,
                       future=True, **pool_kwargs)

if _is_sqlite:
    # sqlite는 기본적으로 FK를 검사하지 않아 MySQL/TiDB와 동작이 다르다.
    # FK 위반을 개발·테스트 단계에서 잡을 수 있도록 커넥션마다 활성화한다.
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_fk(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

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
