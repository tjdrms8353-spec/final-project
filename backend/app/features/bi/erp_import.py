"""Parse ERP-less SME ledgers from CSV/Excel into validated rows."""

import io
from dataclasses import dataclass, field
from datetime import date

import pandas as pd

COLUMN_ALIASES = {
    "date": "date", "일자": "date", "날짜": "date", "거래일": "date",
    "category": "category", "구분": "category", "유형": "category",
    "item": "item", "품목": "item", "항목": "item", "내역": "item",
    "amount": "amount", "금액": "amount",
    "quantity": "quantity", "수량": "quantity",
    "country": "country", "거래국가": "country", "국가": "country",
}
CATEGORY_ALIASES = {
    "sales": "sales", "매출": "sales",
    "purchase": "purchase", "매입": "purchase",
    "expense": "expense", "지출": "expense", "비용": "expense", "판관비": "expense",
    "inventory": "inventory", "재고": "inventory",
}
REQUIRED = ("date", "category", "item", "amount")
MAX_ROWS = 50_000
TEMPLATE_CSV = (
    "date,category,item,amount,quantity,country\n"
    "2026-09-30,sales,DDR5 모듈,1200000000,4000,미국\n"
    "2026-09-30,purchase,실리콘 웨이퍼,520000000,1300,일본\n"
    "2026-09-30,expense,인건비,180000000,,한국\n"
    "2026-09-30,inventory,완제품 재고,610000000,2100,한국\n"
)


@dataclass
class ParsedLedger:
    rows: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    rejected: int = 0


class LedgerFormatError(ValueError):
    pass


def _read(file_name: str, content: bytes) -> pd.DataFrame:
    lower = file_name.lower()
    if lower.endswith((".xlsx", ".xlsm")):
        return pd.read_excel(io.BytesIO(content), dtype=str)
    if lower.endswith(".csv"):
        for encoding in ("utf-8-sig", "cp949"):
            try:
                return pd.read_csv(io.BytesIO(content), dtype=str, encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise LedgerFormatError("CSV 인코딩을 읽을 수 없습니다. UTF-8 또는 CP949로 저장해 주세요.")
    raise LedgerFormatError("CSV(.csv) 또는 Excel(.xlsx) 파일만 업로드할 수 있습니다.")


def _number(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().replace(",", "").replace("₩", "")
    if not text or text.lower() == "nan":
        return None
    return float(text)


def parse_ledger(file_name: str, content: bytes) -> ParsedLedger:
    try:
        frame = _read(file_name, content)
    except LedgerFormatError:
        raise
    except Exception as exc:
        raise LedgerFormatError(f"파일을 읽지 못했습니다: {type(exc).__name__}") from None
    frame = frame.rename(columns={c: COLUMN_ALIASES.get(str(c).strip().lower(), COLUMN_ALIASES.get(str(c).strip(), str(c).strip())) for c in frame.columns})
    missing = [c for c in REQUIRED if c not in frame.columns]
    if missing:
        raise LedgerFormatError(f"필수 열이 없습니다: {', '.join(missing)}")
    if len(frame) > MAX_ROWS:
        raise LedgerFormatError(f"한 번에 최대 {MAX_ROWS}행까지 업로드할 수 있습니다.")
    result = ParsedLedger()
    for index, raw in enumerate(frame.to_dict("records"), start=2):
        try:
            record_date = pd.to_datetime(str(raw["date"]).strip(), errors="raise").date()
            category = CATEGORY_ALIASES.get(str(raw["category"]).strip().lower())
            if category is None:
                raise ValueError(f"구분 값 '{raw['category']}'은 매출/매입/지출/재고 중 하나여야 합니다")
            amount = _number(raw["amount"])
            if amount is None or amount < 0:
                raise ValueError("금액은 0 이상의 숫자여야 합니다")
            item = str(raw.get("item") or "").strip()[:200]
            if not item or item.lower() == "nan":
                raise ValueError("품목이 비어 있습니다")
            country = str(raw.get("country") or "").strip()
            result.rows.append({
                "record_date": record_date if isinstance(record_date, date) else None,
                "category": category, "item": item, "amount": amount,
                "quantity": _number(raw.get("quantity")),
                "country": "한국" if not country or country.lower() == "nan" else country[:50],
            })
        except (ValueError, TypeError) as exc:
            result.rejected += 1
            if len(result.errors) < 20:
                result.errors.append(f"{index}행: {exc}")
    return result
