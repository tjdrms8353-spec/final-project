"""기업 내부 데이터 관리 — 월별 재무 조회/수정 + Excel/CSV 업로드"""
import io
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_write
from ..models import (
    CustomerMonthly, FinancialMonthly, MaterialPurchase, ProductMonthly,
    UploadRecord, User,
)
from ..schemas import (
    CustomerMonthlyIn, MaterialPurchaseIn, MonthlyFinancialIn, ProductMonthlyIn,
)

KIND_SCHEMA = {
    "product_monthly": ProductMonthlyIn,
    "customer_monthly": CustomerMonthlyIn,
    "material_purchase": MaterialPurchaseIn,
}

KIND_UNIQ = {
    "product_monthly": "product_name",
    "customer_monthly": "customer_name",
    "material_purchase": "material_name",
}

router = APIRouter(prefix="/api/financial", tags=["financial"])

MONTHLY_COLS = {
    "month": "month", "revenue": "revenue", "operating_profit": "operating_profit",
    "raw_material_cost": "raw_material_cost", "labor_cost": "labor_cost",
    "other_cost": "other_cost", "export_amount": "export_amount",
    "import_amount": "import_amount", "fx_avg_rate": "fx_avg_rate",
}

KIND_MODELS = {
    "financial_monthly": FinancialMonthly,
    "product_monthly": ProductMonthly,
    "customer_monthly": CustomerMonthly,
    "material_purchase": MaterialPurchase,
}

KIND_LABEL = {
    "financial_monthly": "월별 재무",
    "product_monthly": "제품별 실적",
    "customer_monthly": "거래처별 실적",
    "material_purchase": "원자재 구매",
}

TEMPLATE = pd.DataFrame(columns=[
    "month", "revenue", "operating_profit", "raw_material_cost",
    "labor_cost", "other_cost", "export_amount", "import_amount", "fx_avg_rate",
])
TEMPLATE.loc[0] = ["2026-10", 9000000000, 900000000, 5200000000, 1200000000,
                   1680000000, 5600000000, 3400000000, 1420.0]
TEMPLATE.loc[1] = ["2026-11", 8800000000, 850000000, 5100000000, 1180000000,
                   1650000000, 5500000000, 3300000000, 1435.0]


@router.get("/monthly")
def list_monthly(months: int = 36, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    rows = (
        db.query(FinancialMonthly)
        .filter(FinancialMonthly.company_id == user.company_id)
        .order_by(FinancialMonthly.month.desc())
        .limit(months).all()
    )
    return [
        {"id": r.id, "month": r.month, "revenue": r.revenue,
         "operating_profit": r.operating_profit, "raw_material_cost": r.raw_material_cost,
         "labor_cost": r.labor_cost, "other_cost": r.other_cost,
         "export_amount": r.export_amount, "import_amount": r.import_amount,
         "fx_avg_rate": r.fx_avg_rate}
        for r in rows
    ]


@router.post("/monthly")
def upsert_monthly(body: MonthlyFinancialIn, user: User = Depends(require_write),
                   db: Session = Depends(get_db)):
    if len(body.month) != 7 or body.month[4] != "-":
        raise HTTPException(400, "month 형식은 YYYY-MM 이어야 합니다.")
    row = db.query(FinancialMonthly).filter(
        FinancialMonthly.company_id == user.company_id,
        FinancialMonthly.month == body.month).first()
    if row:
        for k, v in body.model_dump(exclude={"month"}).items():
            setattr(row, k, v)
        action = "FINANCIAL_UPDATE"
    else:
        row = FinancialMonthly(company_id=user.company_id, **body.model_dump())
        db.add(row)
        action = "FINANCIAL_CREATE"
    audit(db, user, action, "financial_monthly", body.month,
          f"매출 {body.revenue:,.0f}원")
    db.commit()
    db.refresh(row)
    # 데이터 변경 → 자동 분석 파이프라인 실행 (백그라운드가 아닌 동기 실행, 데모 규모상 충분)
    from ..services.analysis_engine import run_pipeline
    pipe = run_pipeline(db, user.company_id, trigger="upload")
    db.commit()
    return {"id": row.id, "month": row.month, "pipeline": pipe}


@router.delete("/monthly/{month}")
def delete_monthly(month: str, user: User = Depends(require_write),
                   db: Session = Depends(get_db)):
    row = db.query(FinancialMonthly).filter(
        FinancialMonthly.company_id == user.company_id,
        FinancialMonthly.month == month).first()
    if not row:
        raise HTTPException(404, "해당 월 데이터를 찾을 수 없습니다.")
    db.delete(row)
    audit(db, user, "FINANCIAL_DELETE", "financial_monthly", month)
    db.commit()
    return {"ok": True}


@router.get("/records/{data_kind}")
def list_records(data_kind: str, month: str | None = None,
                 user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """제품별/거래처별/원자재 데이터 목록 조회"""
    model = KIND_MODELS.get(data_kind)
    if not model or data_kind == "financial_monthly":
        raise HTTPException(400, f"지원하지 않는 데이터 종류입니다: {data_kind}")
    q = db.query(model).filter(model.company_id == user.company_id)
    if month:
        q = q.filter(model.month == month)
    rows = q.order_by(model.month.desc()).limit(200).all()
    return [
        {c.name: getattr(r, c.name) for c in model.__table__.columns if c.name != "company_id"}
        for r in rows
    ]


@router.post("/records/{data_kind}")
def upsert_record(data_kind: str, body: dict,
                  user: User = Depends(require_write),
                  db: Session = Depends(get_db)):
    """제품별/거래처별/원자재 데이터 단건 등록·수정 (month + 명칭 기준 upsert)"""
    model = KIND_MODELS.get(data_kind)
    schema = KIND_SCHEMA.get(data_kind)
    uniq = KIND_UNIQ.get(data_kind)
    if not model or not schema:
        raise HTTPException(400, f"지원하지 않는 데이터 종류입니다: {data_kind}")
    try:
        data = schema(**body)
    except Exception as e:
        raise HTTPException(400, f"입력 형식 오류: {e}")
    month = data.month
    if len(month) != 7 or month[4] != "-":
        raise HTTPException(400, "month 형식은 YYYY-MM 이어야 합니다.")

    name_val = getattr(data, uniq)
    row = db.query(model).filter(
        model.company_id == user.company_id,
        model.month == month,
        getattr(model, uniq) == name_val).first()
    if row:
        for k, v in data.model_dump().items():
            setattr(row, k, v)
        action = f"{data_kind.upper()}_UPDATE"
    else:
        row = model(company_id=user.company_id, **data.model_dump())
        db.add(row)
        action = f"{data_kind.upper()}_CREATE"
    audit(db, user, action, data_kind, f"{month}/{name_val}")
    db.commit()
    db.refresh(row)
    return {"id": row.id, "ok": True}


@router.delete("/records/{data_kind}/{record_id}")
def delete_record(data_kind: str, record_id: int,
                  user: User = Depends(require_write),
                  db: Session = Depends(get_db)):
    model = KIND_MODELS.get(data_kind)
    if not model or data_kind == "financial_monthly":
        raise HTTPException(400, f"지원하지 않는 데이터 종류입니다: {data_kind}")
    row = db.query(model).filter(
        model.id == record_id, model.company_id == user.company_id).first()
    if not row:
        raise HTTPException(404, "데이터를 찾을 수 없습니다.")
    db.delete(row)
    audit(db, user, f"{data_kind.upper()}_DELETE", data_kind, record_id)
    db.commit()
    return {"ok": True}


@router.get("/uploads")
def list_uploads(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(UploadRecord)
        .filter(UploadRecord.company_id == user.company_id)
        .order_by(UploadRecord.created_at.desc()).limit(50).all()
    )
    return [
        {"id": u.id, "filename": u.filename, "file_type": u.file_type,
         "data_kind": u.data_kind, "data_kind_label": KIND_LABEL.get(u.data_kind, u.data_kind),
         "status": u.status, "row_count": u.row_count, "warnings": u.warnings,
         "error": u.error, "uploaded_by": u.uploaded_by,
         "created_at": u.created_at.isoformat() if u.created_at else ""}
        for u in rows
    ]


@router.get("/template")
def download_template():
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        TEMPLATE.to_excel(w, index=False, sheet_name="financial_monthly")
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=dayribbon_upload_template.xlsx"})


MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB


def _read_upload(file: UploadFile) -> pd.DataFrame:
    name = (file.filename or "").lower()
    content = file.file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"파일 크기가 {MAX_UPLOAD_BYTES // (1024*1024)}MB를 초과합니다.")
    if name.endswith(".csv"):
        for enc in ("utf-8-sig", "cp949", "utf-8"):
            try:
                return pd.read_csv(io.BytesIO(content), encoding=enc)
            except Exception:
                continue
        raise HTTPException(400, "CSV 파일을 읽을 수 없습니다. 인코딩(UTF-8/CP949)을 확인하세요.")
    if name.endswith((".xlsx", ".xls")):
        try:
            return pd.read_excel(io.BytesIO(content))
        except Exception as e:
            raise HTTPException(400, f"Excel 파일을 읽을 수 없습니다: {e}")
    raise HTTPException(400, "지원하지 않는 파일 형식입니다. .csv 또는 .xlsx 파일을 업로드하세요.")


COL_ALIAS = {
    "월": "month", "월별": "month", "기간": "month",
    "매출": "revenue", "매출액": "revenue", "영업이익": "operating_profit",
    "원자재비": "raw_material_cost", "원자재": "raw_material_cost",
    "인건비": "labor_cost", "기타비용": "other_cost",
    "수출액": "export_amount", "수입액": "import_amount", "환율": "fx_avg_rate",
    "제품명": "product_name", "제품": "product_name",
    "거래처": "customer_name", "거래처명": "customer_name", "국가": "country",
    "원자재명": "material_name", "원자재품목": "material_name",
    "금액": "amount_krw", "비용": "amount_krw", "원가": "cost",
}


def _required_cols(data_kind: str) -> set:
    required = {"month"}
    if data_kind == "financial_monthly":
        required |= {"revenue", "operating_profit"}
    elif data_kind == "product_monthly":
        required |= {"product_name", "revenue", "cost"}
    elif data_kind == "customer_monthly":
        required |= {"customer_name", "revenue"}
    elif data_kind == "material_purchase":
        required |= {"material_name", "amount_krw"}
    return required


def _prepare_df(df: pd.DataFrame, data_kind: str) -> tuple[pd.DataFrame, list[str]]:
    """컬럼 정규화·검증·형변환. 실패 시 HTTPException. 미리보기/확정이 공유한다."""
    warnings = []
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={c: COL_ALIAS.get(c, c) for c in df.columns})

    if df.isna().any().any():
        na_cols = [c for c in df.columns if df[c].isna().any()]
        warnings.append(f"결측치 발견 컬럼: {', '.join(na_cols)}")
    dup_count = int(df.duplicated().sum())
    if dup_count:
        warnings.append(f"중복 행 {dup_count}건 발견 (업로드 시 중복 제거됨)")
        df = df.drop_duplicates()

    missing = _required_cols(data_kind) - set(df.columns)
    if missing:
        raise HTTPException(400, f"필수 컬럼이 없습니다: {', '.join(missing)}. 템플릿을 다운로드해 형식을 맞춰주세요.")

    num_cols = [c for c in df.columns if c not in ("month", "product_name", "customer_name",
                                                    "material_name", "country", "currency")]
    for c in num_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    total_rows = len(df)
    df = df[df["month"].astype(str).str.match(r"^\d{4}-\d{2}$")]
    dropped = total_rows - len(df)
    if dropped:
        warnings.append(f"'YYYY-MM' 형식이 아닌 행 {dropped}건 제외")
    if df.empty:
        raise HTTPException(400, "유효한 'YYYY-MM' 형식의 month 데이터가 없습니다.")
    return df, warnings


@router.post("/upload/preview")
async def upload_preview(file: UploadFile = File(...), data_kind: str = "financial_monthly",
                         user: User = Depends(require_write), db: Session = Depends(get_db)):
    """업로드 미리보기 — 파싱·검증 결과만 반환하고 저장하지 않는다."""
    if data_kind not in KIND_MODELS:
        raise HTTPException(400, f"지원하지 않는 데이터 종류입니다: {data_kind}")
    df = _read_upload(file)
    df, warnings = _prepare_df(df, data_kind)
    return {
        "filename": file.filename, "data_kind": data_kind,
        "data_kind_label": KIND_LABEL.get(data_kind, data_kind),
        "row_count": len(df), "columns": list(df.columns),
        "preview": df.head(10).fillna("").astype(str).to_dict(orient="records"),
        "warnings": warnings,
        "note": "미리보기입니다. '업로드 확정'을 눌러야 저장됩니다.",
    }


@router.post("/upload")
async def upload(file: UploadFile = File(...), data_kind: str = "financial_monthly",
                 user: User = Depends(require_write), db: Session = Depends(get_db)):
    if data_kind not in KIND_MODELS:
        raise HTTPException(400, f"지원하지 않는 데이터 종류입니다: {data_kind}")

    rec = UploadRecord(company_id=user.company_id, filename=file.filename or "upload",
                       file_type=(file.filename or "").rsplit(".", 1)[-1],
                       data_kind=data_kind, status="검증 중", uploaded_by=user.name)
    db.add(rec)
    db.flush()

    try:
        df = _read_upload(file)
        df, warnings = _prepare_df(df, data_kind)
    except HTTPException as e:
        rec.status, rec.error = "오류", str(e.detail)
        audit(db, user, "DATA_UPLOAD_FAIL", "upload", rec.id, rec.error)
        db.commit()
        raise

    model = KIND_MODELS[data_kind]
    num_cols = [c for c in df.columns if c not in ("month", "product_name", "customer_name",
                                                    "material_name", "country", "currency")]

    # upsert 저장
    inserted = 0
    updated = 0
    for _, row in df.iterrows():
        month = str(row["month"])
        filters = {"company_id": user.company_id, "month": month}
        for k in ("product_name", "customer_name", "material_name"):
            if k in model.__table__.columns and k in df.columns and df[k].notna().all():
                filters[k] = str(row.get(k, ""))
        existing = db.query(model).filter_by(**filters).first()
        values = {c: (float(row[c]) if c in num_cols else str(row.get(c, "")))
                  for c in df.columns if c in model.__table__.columns and c != "id"}
        values = {k: v for k, v in values.items() if k != "month"}
        if existing:
            for k, v in values.items():
                setattr(existing, k, v)
            updated += 1
        else:
            db.add(model(company_id=user.company_id, month=month, **values))
            inserted += 1

    rec.row_count = len(df)
    rec.warnings = " | ".join(warnings)
    rec.status = "완료"
    audit(db, user, "DATA_UPLOAD", "upload", rec.id,
          f"{file.filename} ({data_kind}) {len(df)}행 — 신규 {inserted}, 갱신 {updated}")
    db.commit()

    pipe = None
    if data_kind == "financial_monthly":
        from ..services.analysis_engine import run_pipeline
        pipe = run_pipeline(db, user.company_id, trigger="upload")
        db.commit()

    return {"upload_id": rec.id, "status": "완료", "row_count": len(df),
            "inserted": inserted, "updated": updated, "warnings": warnings,
            "pipeline": pipe}
