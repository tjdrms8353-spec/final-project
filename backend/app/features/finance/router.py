from fastapi import APIRouter
from .service import get_status

router = APIRouter(tags=["finance"])

@router.get("/status")
def status():
    return get_status()
