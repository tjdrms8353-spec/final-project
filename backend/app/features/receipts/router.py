from fastapi import APIRouter
from .service import get_status

router = APIRouter(prefix="/receipts", tags=["receipts"])

@router.get("/status")
def status():
    return get_status()
