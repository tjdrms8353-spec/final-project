from fastapi import APIRouter
from .service import get_status

router = APIRouter(prefix="/finance", tags=["finance"])

@router.get("/status")
def status():
    return get_status()
