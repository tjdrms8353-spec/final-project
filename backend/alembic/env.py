"""Alembic 환경 — app.config의 DATABASE_URL과 모델 메타데이터를 사용한다."""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.config import DATABASE_URL  # noqa: E402
from app.database import Base, engine  # noqa: E402
from app import models  # noqa: E402,F401  (메타데이터 등록용)

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# 이 프로젝트 전용 버전 테이블 — 같은 데이터베이스를 공유하는
# 다른 프로젝트의 alembic_version과 충돌하지 않도록 분리한다.
VERSION_TABLE = "dayribbon_alembic_version"


def run_migrations_offline() -> None:
    context.configure(url=DATABASE_URL, target_metadata=target_metadata,
                      literal_binds=True, dialect_opts={"paramstyle": "named"},
                      render_as_batch=DATABASE_URL.startswith("sqlite"),
                      version_table=VERSION_TABLE)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # app.database의 엔진 재사용 — TLS 등 connect_args가 그대로 적용된다.
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == "sqlite",
                          version_table=VERSION_TABLE)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
