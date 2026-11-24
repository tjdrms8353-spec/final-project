"""KPI calculation with Polars and a linear sales trend with scikit-learn.

All numbers shown to users come from here (or SQL), never from the LLM.
"""

import polars as pl
from sklearn.linear_model import LinearRegression

DOMESTIC = {"한국", "대한민국", "korea", "south korea", "kr", "kor"}


def _pct(numerator: float, denominator: float) -> float | None:
    return round(numerator / denominator * 100, 2) if denominator else None


def monthly_summary(records: list[dict]) -> list[dict]:
    """records: dicts with record_date, category, amount, country."""
    if not records:
        return []
    frame = pl.DataFrame(records).with_columns(
        pl.col("record_date").cast(pl.Date),
        pl.col("amount").cast(pl.Float64),
        pl.col("record_date").dt.strftime("%Y-%m").alias("period"),
        (~pl.col("country").str.to_lowercase().is_in(list(DOMESTIC))).alias("foreign"),
    )
    flows = frame.filter(pl.col("category") != "inventory").group_by("period").agg(
        pl.col("amount").filter(pl.col("category") == "sales").sum().alias("sales"),
        pl.col("amount").filter(pl.col("category") == "purchase").sum().alias("purchase"),
        pl.col("amount").filter(pl.col("category") == "expense").sum().alias("expense"),
        pl.col("amount").filter((pl.col("category") == "sales") & pl.col("foreign")).sum().alias("export_sales"),
        pl.col("amount").filter((pl.col("category") == "purchase") & pl.col("foreign")).sum().alias("fx_purchase"),
    )
    inventory = frame.filter(pl.col("category") == "inventory")
    if inventory.height:
        last_dates = inventory.group_by("period").agg(pl.col("record_date").max().alias("last_date"))
        inventory = inventory.join(last_dates, on="period").filter(pl.col("record_date") == pl.col("last_date")) \
            .group_by("period").agg(pl.col("amount").sum().alias("inventory"))
        flows = flows.join(inventory, on="period", how="full", coalesce=True)
    else:
        flows = flows.with_columns(pl.lit(None, dtype=pl.Float64).alias("inventory"))
    rows = flows.fill_null(0.0).sort("period").to_dicts()
    previous = None
    for row in rows:
        sales, purchase, expense = row["sales"], row["purchase"], row["expense"]
        row["operating_profit"] = round(sales - purchase - expense, 2)
        row["gross_margin_pct"] = _pct(sales - purchase, sales)
        row["expense_ratio_pct"] = _pct(expense, sales)
        row["purchase_ratio_pct"] = _pct(purchase, sales)
        row["inventory_days"] = round(row["inventory"] / purchase * 30, 1) if purchase and row["inventory"] else None
        row["fx_purchase_share_pct"] = _pct(row["fx_purchase"], purchase)
        row["export_share_pct"] = _pct(row["export_sales"], sales)
        row["sales_mom_pct"] = _pct(sales - previous["sales"], previous["sales"]) if previous else None
        previous = row
    return rows


def sales_trend(rows: list[dict]) -> dict | None:
    """Linear fit over monthly sales; needs at least 3 months."""
    if len(rows) < 3:
        return None
    x = [[i] for i in range(len(rows))]
    y = [r["sales"] for r in rows]
    model = LinearRegression().fit(x, y)
    r2 = float(model.score(x, y))
    return {
        "months": len(rows),
        "slope_per_month": round(float(model.coef_[0]), 2),
        "next_month_projection": round(float(model.predict([[len(rows)]])[0]), 2),
        "r2": round(r2, 3),
    }
