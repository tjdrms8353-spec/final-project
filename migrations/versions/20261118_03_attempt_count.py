"""Track RSS request attempts."""
from alembic import op
import sqlalchemy as sa
revision = "20261118_03"
down_revision = "20261118_02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("news_collection_runs", sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("news_collection_runs", "attempt_count")
