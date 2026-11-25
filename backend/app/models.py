from datetime import datetime

from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow():
    return datetime.utcnow()


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 신규 등록 기업은 빈 상태로 시작 (데모 기본값 없음 — 시드가 명시적으로 채움)
    name: Mapped[str] = mapped_column(String(200), default="")
    industry: Mapped[str] = mapped_column(String(100), default="")
    size: Mapped[str] = mapped_column(String(50), default="")
    products: Mapped[str] = mapped_column(Text, default="")
    key_customers: Mapped[str] = mapped_column(Text, default="")
    export_countries: Mapped[str] = mapped_column(Text, default="")
    import_countries: Mapped[str] = mapped_column(Text, default="")
    raw_materials: Mapped[str] = mapped_column(Text, default="")
    export_import_ratio: Mapped[str] = mapped_column(String(50), default="")
    annual_revenue: Mapped[float] = mapped_column(Float, default=0)
    annual_raw_material_cost: Mapped[float] = mapped_column(Float, default=0)
    fx_settlement_ratio: Mapped[float] = mapped_column(Float, default=0)  # 외화 결제 비중
    interest_areas: Mapped[str] = mapped_column(Text, default="")
    risk_concerns: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    users = relationship("User", back_populates="company")
    financial_monthly = relationship("FinancialMonthly", back_populates="company", cascade="all, delete-orphan")
    products_data = relationship("ProductMonthly", back_populates="company", cascade="all, delete-orphan")
    customers_data = relationship("CustomerMonthly", back_populates="company", cascade="all, delete-orphan")
    material_purchases = relationship("MaterialPurchase", back_populates="company", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    # 현재 활성 기업. 회원가입 직후(기업 미소속)에는 NULL
    company_id: Mapped[int | None] = mapped_column(
        ForeignKey("companies.id"), index=True, nullable=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    name: Mapped[str] = mapped_column(String(100))
    role: Mapped[str] = mapped_column(String(20), default="MEMBER")  # OWNER/ADMIN/MEMBER/VIEWER (활성 기업 기준)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    company = relationship("Company", back_populates="users")
    memberships = relationship("Membership", back_populates="user",
                               cascade="all, delete-orphan")


class Membership(Base):
    """사용자-기업 소속 관계 (사용자는 여러 기업 워크스페이스에 소속 가능)"""

    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "company_id", name="uq_membership"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="MEMBER")  # OWNER/ADMIN/MEMBER/VIEWER
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    user = relationship("User", back_populates="memberships")
    company = relationship("Company")


class CompanyInvite(Base):
    """기업 사용자 초대. 초대 토큰은 해시로만 저장한다."""

    __tablename__ = "company_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    email: Mapped[str] = mapped_column(String(200), index=True)
    role: Mapped[str] = mapped_column(String(20), default="MEMBER")  # ADMIN/MEMBER/VIEWER (OWNER 초대 불가)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending/accepted/expired/cancelled
    invited_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    accepted_by: Mapped[str] = mapped_column(String(200), default="")


class PasswordResetToken(Base):
    """비밀번호 재설정 토큰 (해시 저장, 1회용). 이메일 발송 모듈 연동 대기 구조."""

    __tablename__ = "password_reset_tokens"

    token_hash: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used: Mapped[bool] = mapped_column(Boolean, default=False)


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime)


class FinancialMonthly(Base):
    __tablename__ = "financial_monthly"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)  # YYYY-MM
    revenue: Mapped[float] = mapped_column(Float, default=0)
    operating_profit: Mapped[float] = mapped_column(Float, default=0)
    raw_material_cost: Mapped[float] = mapped_column(Float, default=0)
    labor_cost: Mapped[float] = mapped_column(Float, default=0)
    other_cost: Mapped[float] = mapped_column(Float, default=0)
    export_amount: Mapped[float] = mapped_column(Float, default=0)
    import_amount: Mapped[float] = mapped_column(Float, default=0)
    fx_avg_rate: Mapped[float] = mapped_column(Float, default=0)  # 당월 평균 원/달러 환율

    company = relationship("Company", back_populates="financial_monthly")


class ProductMonthly(Base):
    __tablename__ = "product_monthly"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    product_name: Mapped[str] = mapped_column(String(200))
    revenue: Mapped[float] = mapped_column(Float, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0)

    company = relationship("Company", back_populates="products_data")


class CustomerMonthly(Base):
    __tablename__ = "customer_monthly"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    customer_name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100), default="")
    revenue: Mapped[float] = mapped_column(Float, default=0)

    company = relationship("Company", back_populates="customers_data")


class MaterialPurchase(Base):
    __tablename__ = "material_purchases"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    material_name: Mapped[str] = mapped_column(String(200))
    amount_krw: Mapped[float] = mapped_column(Float, default=0)
    currency: Mapped[str] = mapped_column(String(10), default="KRW")

    company = relationship("Company", back_populates="material_purchases")


class MarketSeries(Base):
    """환율/금리/지수/원자재 등 범용 시계열 데이터"""

    __tablename__ = "market_series"
    # 기업·시리즈·월 조합은 하나만 존재 (수집 upsert의 중복 차단 키)
    __table_args__ = (
        UniqueConstraint("company_id", "series_key", "month", name="uq_market_series"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=True)
    series_key: Mapped[str] = mapped_column(String(50), index=True)  # USD_KRW, BASE_RATE, KOSPI, ...
    series_name: Mapped[str] = mapped_column(String(200))
    unit: Mapped[str] = mapped_column(String(50), default="")
    source: Mapped[str] = mapped_column(String(200), default="(데모) 내부 생성 데이터")
    month: Mapped[str] = mapped_column(String(7), index=True)
    value: Mapped[float] = mapped_column(Float)


class NewsItem(Base):
    __tablename__ = "news_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(200), default="(데모) 산업 뉴스")
    link: Mapped[str] = mapped_column(String(500), default="")  # 원문 링크 — 실수집 뉴스 출처 표기·중복 차단 키
    category: Mapped[str] = mapped_column(String(50), default="산업동향")  # 반도체/정책/거시경제/공급망/환율 등
    sentiment: Mapped[str] = mapped_column(String(20), default="neutral")  # positive/negative/neutral
    relevance_score: Mapped[float] = mapped_column(Float, default=0)  # 0~100
    importance: Mapped[str] = mapped_column(String(20), default="보통")  # 높음/보통/낮음
    impact_on_company: Mapped[str] = mapped_column(Text, default="")
    why_relevant: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    analysis_type: Mapped[str] = mapped_column(String(20))  # growth / direction / risk
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict] = mapped_column(JSON, default=dict)  # 수치/근거/데이터 목록 등
    data_sources: Mapped[str] = mapped_column(Text, default="")
    basis_date: Mapped[str] = mapped_column(String(20), default="")
    impact: Mapped[str] = mapped_column(Text, default="")
    uncertainty: Mapped[str] = mapped_column(Text, default="")
    suggestions: Mapped[str] = mapped_column(Text, default="")
    engine: Mapped[str] = mapped_column(String(50), default="rule-based-demo")
    status: Mapped[str] = mapped_column(String(20), default="검토 대기")  # 검토 대기/검토 중/수용/보류/미수용/처리 완료
    trigger: Mapped[str] = mapped_column(String(100), default="manual")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_by: Mapped[str] = mapped_column(String(100), default="")
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)


class RiskAlert(Base):
    __tablename__ = "risk_alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    severity: Mapped[str] = mapped_column(String(10))  # 정상/관심/주의/위험/심각
    category: Mapped[str] = mapped_column(String(50), default="")
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text, default="")
    related_type: Mapped[str] = mapped_column(String(50), default="")
    related_id: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="unread")  # unread/read/acknowledged
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    analysis_result_id: Mapped[int] = mapped_column(ForeignKey("analysis_results.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="검토 대기")
    decision: Mapped[str] = mapped_column(String(20), default="")  # 수용/보류/미수용
    reason: Mapped[str] = mapped_column(Text, default="")
    assignee: Mapped[str] = mapped_column(String(100), default="")
    due_date: Mapped[str] = mapped_column(String(20), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    follow_ups = relationship("FollowUp", back_populates="decision", cascade="all, delete-orphan")


class FollowUp(Base):
    __tablename__ = "follow_ups"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    decision_id: Mapped[int] = mapped_column(ForeignKey("decisions.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="등록")  # 등록/진행 중/완료
    assignee: Mapped[str] = mapped_column(String(100), default="")
    due_date: Mapped[str] = mapped_column(String(20), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    decision = relationship("Decision", back_populates="follow_ups")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    ntype: Mapped[str] = mapped_column(String(50), default="risk")  # risk/news/kpi/analysis/report/weekly
    title: Mapped[str] = mapped_column(String(300))
    message: Mapped[str] = mapped_column(Text, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), unique=True)
    risk_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    important_news: Mapped[bool] = mapped_column(Boolean, default=True)
    kpi_change: Mapped[bool] = mapped_column(Boolean, default=True)
    analysis_done: Mapped[bool] = mapped_column(Boolean, default=True)
    weekly_summary: Mapped[bool] = mapped_column(Boolean, default=True)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    kakao_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    email_address: Mapped[str] = mapped_column(String(200), default="")


class UploadRecord(Base):
    __tablename__ = "upload_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    file_type: Mapped[str] = mapped_column(String(20))
    data_kind: Mapped[str] = mapped_column(String(50), default="financial_monthly")  # financial_monthly/product_monthly/customer_monthly/material_purchase
    status: Mapped[str] = mapped_column(String(20), default="검증 대기")  # 완료/오류/검증 대기
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    warnings: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    uploaded_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    period: Mapped[str] = mapped_column(String(20))  # e.g. 2025-10
    title: Mapped[str] = mapped_column(String(300))
    content: Mapped[dict] = mapped_column(JSON, default=dict)
    pdf_path: Mapped[str] = mapped_column(String(500), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=True)
    user_name: Mapped[str] = mapped_column(String(100), default="(시스템)")
    user_role: Mapped[str] = mapped_column(String(20), default="")
    action: Mapped[str] = mapped_column(String(100), index=True)
    target_type: Mapped[str] = mapped_column(String(100), default="")
    target_id: Mapped[str] = mapped_column(String(50), default="")
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class DemoEvent(Base):
    """데모용 시장 이벤트 (실제 금융 데이터가 아닌 테스트 이벤트)"""

    __tablename__ = "demo_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(50))
    description: Mapped[str] = mapped_column(String(300), default="")
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
