"""audit_logs.company_id nullable — 기업 미등록 사용자의 감사 로그 허용

기업 등록 전(회원가입·로그인 등) 사용자의 audit()이 company_id=0을 쓰면
FK(companies.id) 위반으로 commit이 실패한다 — TiDB는 FK를 검사하므로
운영에서 register/login이 500을 반환했다. NULL을 허용해 수정.

Revision ID: a1c8e3f9d204
Revises: 32f91f6f7a5d
Create Date: 2026-11-26

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1c8e3f9d204'
down_revision = '32f91f6f7a5d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # sqlite는 ALTER COLUMN 미지원 — batch 모드(테이블 재생성)로 통일.
    # mysql/TiDB에서도 동일하게 동작한다.
    with op.batch_alter_table('audit_logs') as batch:
        batch.alter_column('company_id',
                           existing_type=sa.Integer(), nullable=True)


def downgrade() -> None:
    # NULL 행(기업 미등록 이벤트)은 NOT NULL 복원이 불가하므로 삭제 후 복원
    op.execute("DELETE FROM audit_logs WHERE company_id IS NULL")
    with op.batch_alter_table('audit_logs') as batch:
        batch.alter_column('company_id',
                           existing_type=sa.Integer(), nullable=False)
