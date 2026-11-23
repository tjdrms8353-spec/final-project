"""Machine translations of foreign article titles and summaries."""
from alembic import op
import sqlalchemy as sa

revision = "20261123_06"
down_revision = "20261119_05"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "news_translations",
        sa.Column("url_hash", sa.String(64), primary_key=True),
        sa.Column("lang", sa.String(8), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(20), nullable=False),
        sa.Column("translated_at", sa.DateTime(), nullable=False),
        mysql_charset="utf8mb4",
    )


def downgrade():
    op.drop_table("news_translations")
