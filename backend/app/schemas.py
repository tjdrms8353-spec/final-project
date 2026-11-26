from pydantic import BaseModel, Field
from typing import Optional


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)
    name: str = Field(min_length=1, max_length=100)


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    email: str


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class CompanyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    industry: str = ""
    size: str = ""
    products: str = ""
    key_customers: str = ""
    export_countries: str = ""
    import_countries: str = ""
    raw_materials: str = ""
    export_import_ratio: str = ""
    annual_revenue: float = 0
    annual_raw_material_cost: float = 0
    fx_settlement_ratio: float = 0
    interest_areas: str = ""
    risk_concerns: str = ""


class CompanySelect(BaseModel):
    company_id: int


class InviteCreate(BaseModel):
    email: str
    role: str = "MEMBER"  # ADMIN/MEMBER/VIEWER


class InviteAccept(BaseModel):
    token: str


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    products: Optional[str] = None
    key_customers: Optional[str] = None
    export_countries: Optional[str] = None
    import_countries: Optional[str] = None
    raw_materials: Optional[str] = None
    export_import_ratio: Optional[str] = None
    annual_revenue: Optional[float] = None
    annual_raw_material_cost: Optional[float] = None
    fx_settlement_ratio: Optional[float] = None
    interest_areas: Optional[str] = None
    risk_concerns: Optional[str] = None
    allow_external_ai: Optional[bool] = None   # 외부 AI(LLM) 분석 전송 옵트인


class UserUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None


class SimulationParams(BaseModel):
    fx_change_pct: float = Field(default=3.2, description="환율 변동률 %")
    rate_change_pct: float = Field(default=0.5, description="기준금리 변동폭 %p")
    material_change_pct: float = Field(default=5.0, description="원자재 가격 변동률 %")
    annual_import_cost: float = Field(default=5_000_000_000, description="연간 수입 비용(원)")
    debt_amount: float = Field(default=10_000_000_000, description="차입금 규모(원)")
    revenue_change_pct: float = Field(default=-3.0, description="매출 변동률 %")


class DecisionCreate(BaseModel):
    analysis_result_id: Optional[int] = None
    status: str = "검토 대기"
    decision: str = ""
    reason: str = ""
    assignee: str = ""
    due_date: str = ""


class DecisionUpdate(BaseModel):
    status: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None


class FollowUpCreate(BaseModel):
    decision_id: Optional[int] = None
    analysis_result_id: Optional[int] = None
    title: str
    assignee: str = ""
    due_date: str = ""


class FollowUpUpdate(BaseModel):
    status: Optional[str] = None
    assignee: Optional[str] = None
    due_date: Optional[str] = None
    title: Optional[str] = None


class NotificationSettingUpdate(BaseModel):
    risk_alert: Optional[bool] = None
    important_news: Optional[bool] = None
    kpi_change: Optional[bool] = None
    analysis_done: Optional[bool] = None
    weekly_summary: Optional[bool] = None
    email_enabled: Optional[bool] = None
    kakao_enabled: Optional[bool] = None
    email_address: Optional[str] = None
    kakao_phone: Optional[str] = None


class MonthlyFinancialIn(BaseModel):
    month: str
    revenue: float = 0
    operating_profit: float = 0
    raw_material_cost: float = 0
    labor_cost: float = 0
    other_cost: float = 0
    export_amount: float = 0
    import_amount: float = 0
    fx_avg_rate: float = 0
    net_income: Optional[float] = None
    assets: Optional[float] = None
    liabilities: Optional[float] = None
    inventory: Optional[float] = None
    borrowings: Optional[float] = None
    current_assets: Optional[float] = None
    current_liabilities: Optional[float] = None


class ProductMonthlyIn(BaseModel):
    month: str
    product_name: str
    revenue: float = 0
    cost: float = 0


class CustomerMonthlyIn(BaseModel):
    month: str
    customer_name: str
    country: str = ""
    revenue: float = 0


class MaterialPurchaseIn(BaseModel):
    month: str
    material_name: str
    amount_krw: float = 0
    currency: str = "KRW"


class AnalysisReview(BaseModel):
    status: str  # 검토 중/수용/보류/미수용/처리 완료
    note: str = ""
