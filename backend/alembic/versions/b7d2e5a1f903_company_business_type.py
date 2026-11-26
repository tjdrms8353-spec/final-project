"""companies.business_type — 사업자 유형 (법인/개인사업자)

기업 워크스페이스의 사업자 형태를 기록한다. 개인사업자는 DART 공시 등
법인 전용 공급처 적용 대상이 아니므로 분석·수집 로직에서 구분에 사용.
기존 기업에는 'corporation' 기본값을 채운다.

Revision ID: b7d2e5a1f903
Revises: a1c8e3f9d204
Create Date: 2026-11-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'b7d2e5a1f903'
down_revision = 'a1c8e3f9d204'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('companies') as batch:
        batch.add_column(sa.Column(
            'business_type', sa.String(length=20),
            nullable=False, server_default='corporation'))


def downgrade() -> None:
    with op.batch_alter_table('companies') as batch:
        batch.drop_column('business_type')
