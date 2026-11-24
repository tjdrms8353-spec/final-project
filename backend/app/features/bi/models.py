"""dayribbon BI tables (companies, ERP uploads, market data, analyses, decisions)."""

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BiUser(Base):
    __tablename__ = "bi_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class Company(Base):
    __tablename__ = "bi_companies"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(50))
    main_products: Mapped[list] = mapped_column(JSON)
    interest_industries: Mapped[list] = mapped_column(JSON)
    trade_countries: Mapped[list] = mapped_column(JSON)
    interest_indicators: Mapped[list] = mapped_column(JSON)
    created_by: Mapped[int] = mapped_column(ForeignKey("bi_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class CompanyMember(Base):
    """Per-company role: OWNER and APPROVER may decide; ANALYST may upload/analyze; VIEWER reads."""
    __tablename__ = "bi_company_members"
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("bi_users.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))


class ErpUpload(Base):
    __tablename__ = "bi_erp_uploads"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    file_name: Mapped[str] = mapped_column(String(255))
    row_count: Mapped[int] = mapped_column(Integer)
    rejected_count: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("bi_users.id"))
    uploaded_at: Mapped[datetime] = mapped_column(DateTime)


class ErpRecord(Base):
    __tablename__ = "bi_erp_records"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    upload_id: Mapped[int] = mapped_column(ForeignKey("bi_erp_uploads.id"))
    record_date: Mapped[date] = mapped_column(Date)
    # sales | purchase | expense | inventory
    category: Mapped[str] = mapped_column(String(20))
    item: Mapped[str] = mapped_column(String(200))
    amount: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float | None] = mapped_column(Float)
    country: Mapped[str] = mapped_column(String(50))
    __table_args__ = (Index("ix_bi_erp_records_company_date", "company_id", "record_date"),)


class MarketIndicator(Base):
    __tablename__ = "bi_market_indicators"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(30))
    obs_date: Mapped[date] = mapped_column(Date)
    value: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(Text)
    collected_at: Mapped[datetime] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("code", "obs_date", name="uq_bi_market_code_date"),)


class AnalysisRun(Base):
    __tablename__ = "bi_analysis_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    period: Mapped[str] = mapped_column(String(7))
    metrics: Mapped[dict] = mapped_column(JSON)
    narrative: Mapped[str] = mapped_column(Text)
    narrative_source: Mapped[str] = mapped_column(String(20))
    created_by: Mapped[int] = mapped_column(ForeignKey("bi_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime)


class AnalysisFinding(Base):
    __tablename__ = "bi_analysis_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("bi_analysis_runs.id"))
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    # opportunity | risk | change
    kind: Mapped[str] = mapped_column(String(20))
    severity: Mapped[str] = mapped_column(String(10))
    title: Mapped[str] = mapped_column(String(300))
    facts: Mapped[list] = mapped_column(JSON)
    inference: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON)
    uncertainty: Mapped[str] = mapped_column(Text)
    review_points: Mapped[list] = mapped_column(JSON)
    recommendation: Mapped[str] = mapped_column(Text)
    # PENDING | APPROVED | ON_HOLD | REJECTED (latest decision)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")


class Decision(Base):
    __tablename__ = "bi_decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    finding_id: Mapped[int] = mapped_column(ForeignKey("bi_analysis_findings.id"))
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    status: Mapped[str] = mapped_column(String(20))
    reason: Mapped[str] = mapped_column(Text)
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("bi_users.id"))
    decided_by: Mapped[int] = mapped_column(ForeignKey("bi_users.id"))
    decided_at: Mapped[datetime] = mapped_column(DateTime)


class FollowUpAction(Base):
    __tablename__ = "bi_follow_up_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("bi_decisions.id"))
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    title: Mapped[str] = mapped_column(String(300))
    assignee_id: Mapped[int | None] = mapped_column(ForeignKey("bi_users.id"))
    due_date: Mapped[date | None] = mapped_column(Date)
    # OPEN | IN_PROGRESS | DONE
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    updated_at: Mapped[datetime] = mapped_column(DateTime)


class AuditLog(Base):
    """Append-only trail of who did what in a company workspace."""
    __tablename__ = "bi_audit_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("bi_companies.id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("bi_users.id"))
    # COMPANY_CREATED | MEMBER_UPDATED | ERP_UPLOAD | ANALYSIS_RUN | DECISION | ACTION_UPDATE | SIMULATION_RUN | REPORT_GENERATED
    action: Mapped[str] = mapped_column(String(30))
    entity_type: Mapped[str] = mapped_column(String(30))
    entity_id: Mapped[int | None] = mapped_column(Integer)
    detail: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    __table_args__ = (Index("ix_bi_audit_company_time", "company_id", "created_at"),)


BI_TABLES = [m.__table__ for m in (
    BiUser, Company, CompanyMember, ErpUpload, ErpRecord, MarketIndicator,
    AnalysisRun, AnalysisFinding, Decision, FollowUpAction, AuditLog,
)]
