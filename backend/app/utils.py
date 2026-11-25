from datetime import date


def month_range(n: int, end: date | None = None) -> list[str]:
    """최근 n개월의 'YYYY-MM' 리스트 (오름차순). end 미지정 시 이번 달."""
    end = end or date.today()
    y, m = end.year, end.month
    out = []
    for _ in range(n):
        out.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(out))


def prev_month(month: str) -> str:
    y, m = map(int, month.split("-"))
    m -= 1
    if m == 0:
        m, y = 12, y - 1
    return f"{y:04d}-{m:02d}"


def fmt_krw(amount: float) -> str:
    if abs(amount) >= 1e8:
        return f"{amount / 1e8:,.1f}억원"
    if abs(amount) >= 1e4:
        return f"{amount / 1e4:,.0f}만원"
    return f"{amount:,.0f}원"
