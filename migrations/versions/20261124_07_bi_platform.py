"""dayribbon BI: companies, members, ERP uploads, market indicators, analyses, decisions."""
from alembic import op
import sqlalchemy as sa

revision = "20261124_07"
down_revision = "20261123_06"
branch_labels = None
depends_on = None

KW = {"mysql_charset": "utf8mb4"}


def upgrade():
    op.create_table(
        "bi_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), **KW)
    op.create_table(
        "bi_companies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("industry", sa.String(50), nullable=False),
        sa.Column("main_products", sa.JSON(), nullable=False),
        sa.Column("interest_industries", sa.JSON(), nullable=False),
        sa.Column("trade_countries", sa.JSON(), nullable=False),
        sa.Column("interest_indicators", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("bi_users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), **KW)
    op.create_table(
        "bi_company_members",
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("bi_users.id"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False), **KW)
    op.create_table(
        "bi_erp_uploads",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), nullable=False),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("rejected_count", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("bi_users.id"), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False), **KW)
    op.create_table(
        "bi_erp_records",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), nullable=False),
        sa.Column("upload_id", sa.Integer(), sa.ForeignKey("bi_erp_uploads.id"), nullable=False),
        sa.Column("record_date", sa.Date(), nullable=False),
        sa.Column("category", sa.String(20), nullable=False),
        sa.Column("item", sa.String(200), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("country", sa.String(50), nullable=False), **KW)
    op.create_index("ix_bi_erp_records_company_date", "bi_erp_records", ["company_id", "record_date"])
    op.create_table(
        "bi_market_indicators",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("obs_date", sa.Date(), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("collected_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("code", "obs_date", name="uq_bi_market_code_date"), **KW)
    op.create_table(
        "bi_analysis_runs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=False),
        sa.Column("narrative", sa.Text(), nullable=False),
        sa.Column("narrative_source", sa.String(20), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("bi_users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False), **KW)
    op.create_table(
        "bi_analysis_findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("bi_analysis_runs.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("inference", sa.Text(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("uncertainty", sa.Text(), nullable=False),
        sa.Column("review_points", sa.JSON(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), **KW)
    op.create_table(
        "bi_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("finding_id", sa.Integer(), sa.ForeignKey("bi_analysis_findings.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("bi_users.id"), nullable=True),
        sa.Column("decided_by", sa.Integer(), sa.ForeignKey("bi_users.id"), nullable=False),
        sa.Column("decided_at", sa.DateTime(), nullable=False), **KW)
    op.create_table(
        "bi_follow_up_actions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("decision_id", sa.Integer(), sa.ForeignKey("bi_decisions.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("bi_companies.id"), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("bi_users.id"), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False), **KW)


def downgrade():
    for table in ("bi_follow_up_actions", "bi_decisions", "bi_analysis_findings", "bi_analysis_runs",
                  "bi_market_indicators", "bi_erp_records", "bi_erp_uploads", "bi_company_members",
                  "bi_companies", "bi_users"):
        op.drop_table(table)
