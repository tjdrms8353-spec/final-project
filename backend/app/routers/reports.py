"""월간 경영 보고서 — 생성/조회/PDF 다운로드"""
import os

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import audit, get_current_user, require_write
from ..models import Report, User
from ..services.report_service import create_report
from ..utils import month_range

router = APIRouter(prefix="/api/reports", tags=["reports"])


def r_dict(r: Report) -> dict:
    c = r.content or {}
    return {
        "id": r.id, "period": r.period, "title": r.title,
        "created_by": r.created_by,
        "created_at": r.created_at.isoformat() if r.created_at else "",
        "has_pdf": bool(r.pdf_path and os.path.exists(r.pdf_path)),
        "kpi_summary": c.get("kpi_summary", {}),
        "disclaimer": c.get("disclaimer", ""),
    }


@router.get("")
def list_reports(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Report).filter(Report.company_id == user.company_id)
        .order_by(Report.created_at.desc()).limit(60).all()
    )
    return {"items": [r_dict(r) for r in rows], "available_months": month_range(24)}


@router.post("/generate")
def generate(period: str, user: User = Depends(require_write),
             db: Session = Depends(get_db)):
    if len(period) != 7 or period[4] != "-":
        raise HTTPException(400, "period 형식은 YYYY-MM 이어야 합니다.")
    r = create_report(db, user.company_id, period, user.name)
    audit(db, user, "REPORT_GENERATE", "report", r.id, f"{period} 보고서 생성")
    db.commit()
    return r_dict(r)


@router.get("/{report_id}")
def get_report(report_id: int, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r or r.company_id != user.company_id:
        raise HTTPException(404, "보고서를 찾을 수 없습니다.")
    return {**r_dict(r), "content": r.content}


@router.get("/{report_id}/pdf")
def get_pdf(report_id: int, user: User = Depends(get_current_user),
            db: Session = Depends(get_db)):
    r = db.get(Report, report_id)
    if not r or r.company_id != user.company_id:
        raise HTTPException(404, "보고서를 찾을 수 없습니다.")
    if not r.pdf_path or not os.path.exists(r.pdf_path):
        raise HTTPException(404, "PDF 파일이 없습니다. 보고서를 다시 생성해 주세요.")
    audit(db, user, "REPORT_VIEW", "report", r.id)
    db.commit()
    return FileResponse(r.pdf_path, media_type="application/pdf",
                        filename=os.path.basename(r.pdf_path))
