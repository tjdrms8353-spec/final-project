"""notification_deliveries + notification_settings.kakao_phone

Revision ID: 32f91f6f7a5d
Revises: e6b6ad5682bd
Create Date: 2026-11-26 16:12:27.233871

"""
from alembic import op
import sqlalchemy as sa


revision = '32f91f6f7a5d'
down_revision = 'e6b6ad5682bd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'notification_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('company_id', sa.Integer(), nullable=False),
        sa.Column('notification_id', sa.Integer(), nullable=True),
        sa.Column('channel', sa.String(length=20), nullable=False),
        sa.Column('address', sa.String(length=200), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notification_deliveries_company_id',
                    'notification_deliveries', ['company_id'])
    op.create_index('ix_notification_deliveries_notification_id',
                    'notification_deliveries', ['notification_id'])
    op.create_index('ix_notification_deliveries_status',
                    'notification_deliveries', ['status'])
    op.add_column('notification_settings',
                  sa.Column('kakao_phone', sa.String(length=50),
                            nullable=False, server_default=''))


def downgrade() -> None:
    op.drop_column('notification_settings', 'kakao_phone')
    op.drop_index('ix_notification_deliveries_status', 'notification_deliveries')
    op.drop_index('ix_notification_deliveries_notification_id',
                  'notification_deliveries')
    op.drop_index('ix_notification_deliveries_company_id',
                  'notification_deliveries')
    op.drop_table('notification_deliveries')
