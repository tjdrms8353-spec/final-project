from fastapi import APIRouter
from .service import get_status

router = APIRouter(tags=["erp"])

@router.get("/status")
def status():
    return get_status()
