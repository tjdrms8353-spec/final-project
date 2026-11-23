"""Scope interruption recovery to the local project lock owner."""
from alembic import op
import sqlalchemy as sa
revision = '20261118_04'
down_revision = '20261118_03'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('news_collection_runs', sa.Column('owner_id', sa.String(64), nullable=True))


def downgrade():
    op.drop_column('news_collection_runs', 'owner_id')
