"""notification_deliveries.attachment_path — 보고서 PDF 등 첨부 파일 경로

월간 보고서 자동 발송처럼 첨부가 필요한 발송 건의 서버 내 파일 경로를 저장한다.
발송 시점에 파일이 없으면 첨부 없이 본문만 발송한다.

Revision ID: d8f3a1c5e210
Revises: c4e9a1b7f208
Create Date: 2026-11-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'd8f3a1c5e210'
down_revision = 'c4e9a1b7f208'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('notification_deliveries') as batch:
        batch.add_column(sa.Column('attachment_path', sa.String(500),
                                   nullable=False, server_default=''))


def downgrade() -> None:
    with op.batch_alter_table('notification_deliveries') as batch:
        batch.drop_column('attachment_path')
