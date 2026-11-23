"""Collection execution history, without credentials or article payloads."""
from alembic import op
import sqlalchemy as sa

revision = "20261118_02"
down_revision = "20261118_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_collection_runs",
        sa.Column("run_id", sa.String(36), primary_key=True),
        sa.Column("feed", sa.String(50), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime()),
        sa.Column("status", sa.String(20), nullable=False),
        *[sa.Column(name, sa.Integer()) for name in (
            "input_count", "accepted_count", "rejected_count", "duplicate_count",
            "inserted_count", "existing_count", "http_status",
        )],
        sa.Column("error_code", sa.String(50)),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_news_collection_runs_started", "news_collection_runs", ["started_at"])


def downgrade():
    op.drop_index("ix_news_collection_runs_started", table_name="news_collection_runs")
    op.drop_table("news_collection_runs")
