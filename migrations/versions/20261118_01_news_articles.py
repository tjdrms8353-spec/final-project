"""Proposed news storage schema; team review required before shared DB apply."""

from alembic import op
import sqlalchemy as sa

revision = "20261118_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_articles",
        sa.Column("url_hash", sa.String(64), primary_key=True),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("observed_at", sa.DateTime(), nullable=True),
        sa.Column("sort_at", sa.DateTime(), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_news_articles_sort_at", "news_articles", ["sort_at", "url_hash"])


def downgrade():
    op.drop_index("ix_news_articles_sort_at", table_name="news_articles")
    op.drop_table("news_articles")
