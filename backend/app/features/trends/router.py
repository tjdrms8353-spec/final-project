from fastapi import APIRouter
from .service import get_status

router = APIRouter(prefix="/trends", tags=["trends"])

@router.get("/status")
def status():
    return get_status()
