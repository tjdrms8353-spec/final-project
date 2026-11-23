from alembic import context

from app.db.base import Base
from app.db.session import get_database_url, get_engine
import app.models  # Register shared models through this package as they are added.

target_metadata = Base.metadata

if context.is_offline_mode():
    context.configure(
        url=get_database_url(), target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
