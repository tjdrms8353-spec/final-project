"""Publisher section labels and the feed time window of each collection run."""
from alembic import op
import sqlalchemy as sa

revision = "20261119_05"
down_revision = "20261118_04"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_article_sections",
        sa.Column("url_hash", sa.String(64), primary_key=True),
        sa.Column("label", sa.String(100), primary_key=True),
        sa.Column("feed", sa.String(50), nullable=False),
        sa.Column("first_seen_at", sa.DateTime(), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_news_article_sections_label", "news_article_sections", ["label"])
    op.add_column("news_collection_runs", sa.Column("window_start_at", sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column("news_collection_runs", "window_start_at")
    op.drop_index("ix_news_article_sections_label", table_name="news_article_sections")
    op.drop_table("news_article_sections")
