"""Scenario simulation (phase 2): apply percentage shocks to the latest month."""


def simulate(base: dict, fx_pct: float = 0, purchase_price_pct: float = 0,
             sales_pct: float = 0, volume_pct: float = 0) -> dict:
    sales, purchase, expense = base["sales"], base["purchase"], base["expense"]
    export_sales, fx_purchase = base.get("export_sales", 0), base.get("fx_purchase", 0)
    fx, price, s, vol = fx_pct / 100, purchase_price_pct / 100, sales_pct / 100, volume_pct / 100
    new_sales = (sales + export_sales * fx) * (1 + s) * (1 + vol)
    new_purchase = (purchase + fx_purchase * fx) * (1 + price) * (1 + vol)
    before = {"sales": sales, "cost": purchase + expense, "profit": sales - purchase - expense}
    after = {"sales": new_sales, "cost": new_purchase + expense, "profit": new_sales - new_purchase - expense}
    return {
        "period": base["period"],
        "before": {k: round(v, 2) for k, v in before.items()},
        "after": {k: round(v, 2) for k, v in after.items()},
        "delta": {k: round(after[k] - before[k], 2) for k in before},
        "assumptions": [
            "기준값은 가장 최근 월의 업로드 데이터입니다.",
            "환율 변동은 수출 매출(해외 거래국)과 외화 매입(해외 거래국)에만 적용합니다.",
            "판매량 변동은 매출과 매입에 동일 비율로 적용하고, 지출(판관비)은 고정으로 가정합니다.",
            "단순 민감도 계산이며 예측이 아닙니다.",
        ],
    }
