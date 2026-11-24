"""Industry templates. Add a new entry to INDUSTRIES to support another industry."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class KpiDefinition:
    code: str
    label: str
    unit: str
    description: str
    higher_is_better: bool = True


@dataclass(frozen=True)
class IndustryTemplate:
    code: str
    label: str
    kpis: tuple[KpiDefinition, ...]
    news_keywords: tuple[str, ...]
    market_indicators: tuple[str, ...]
    # Thresholds used by rule-based analysis; tuned per industry.
    thresholds: dict[str, float] = field(default_factory=dict)


COMMON_KPIS = (
    KpiDefinition("sales", "월 매출액", "KRW", "업로드된 매출(sales) 합계"),
    KpiDefinition("sales_mom_pct", "매출 전월 대비", "%", "직전 월 대비 매출 증감률"),
    KpiDefinition("gross_margin_pct", "매출총이익률", "%", "(매출 - 매입) / 매출"),
    KpiDefinition("expense_ratio_pct", "판관비 비율", "%", "지출(expense) / 매출", higher_is_better=False),
    KpiDefinition("operating_profit", "영업이익(추정)", "KRW", "매출 - 매입 - 지출"),
)

INDUSTRIES: dict[str, IndustryTemplate] = {
    "semiconductor": IndustryTemplate(
        code="semiconductor",
        label="반도체 제조",
        kpis=COMMON_KPIS + (
            KpiDefinition("purchase_ratio_pct", "원재료 매입 비중", "%", "매입(purchase) / 매출", higher_is_better=False),
            KpiDefinition("inventory_days", "재고 보유일수", "일", "월말 재고금액 / 월 매입 × 30", higher_is_better=False),
            KpiDefinition("fx_purchase_share_pct", "외화 매입 비중", "%", "한국 외 거래국 매입 / 전체 매입", higher_is_better=False),
            KpiDefinition("export_share_pct", "수출 매출 비중", "%", "한국 외 거래국 매출 / 전체 매출"),
        ),
        news_keywords=("반도체", "메모리", "HBM", "파운드리", "D램", "낸드", "수출규제", "semiconductor", "chip"),
        market_indicators=("USD/KRW", "JPY/KRW", "CNY/KRW", "KR_BASE_RATE"),
        thresholds={
            "sales_drop_pct": -5.0,
            "sales_growth_pct": 5.0,
            "margin_drop_pp": -3.0,
            "inventory_days_high": 60.0,
            "fx_move_pct": 3.0,
            "fx_purchase_share_high": 40.0,
        },
    ),
}

DEFAULT_INDUSTRY = "semiconductor"


def get_template(code: str) -> IndustryTemplate:
    return INDUSTRIES.get(code) or INDUSTRIES[DEFAULT_INDUSTRY]


def template_dict(template: IndustryTemplate) -> dict:
    return {
        "code": template.code,
        "label": template.label,
        "kpis": [k.__dict__ for k in template.kpis],
        "news_keywords": list(template.news_keywords),
        "market_indicators": list(template.market_indicators),
    }
