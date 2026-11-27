"""notification_deliveries.company_id nullable — 기업 미소속 발송 건 허용

초대·비밀번호 재설정 같은 트랜잭셔널 발송은 기업 미소속 사용자에게도 갈 수
있으므로 NULL을 허용한다 (audit_logs.company_id와 동일한 FK 패턴).

Revision ID: c4e9a1b7f208
Revises: b7d2e5a1f903
Create Date: 2026-11-27

"""
from alembic import op
import sqlalchemy as sa


revision = 'c4e9a1b7f208'
down_revision = 'b7d2e5a1f903'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('notification_deliveries') as batch:
        batch.alter_column('company_id',
                           existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    op.execute("DELETE FROM notification_deliveries WHERE company_id IS NULL")
    with op.batch_alter_table('notification_deliveries') as batch:
        batch.alter_column('company_id',
                           existing_type=sa.Integer(), nullable=False)
