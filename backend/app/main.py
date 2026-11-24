from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings
from app.features.trends.router import router as trends_router
from app.features.finance.router import router as finance_router
from app.features.receipts.router import router as receipts_router
from app.features.bi.router import router as bi_router

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware, allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
for router, prefix, legacy in (
    (trends_router, "/api/news", "/api/v1/trends"),
    (finance_router, "/api/finance", "/api/v1/finance"),
    (receipts_router, "/api/erp", "/api/v1/receipts"),
):
    app.include_router(router, prefix=prefix)
    app.include_router(router, prefix=legacy, include_in_schema=False)
app.include_router(bi_router, prefix="/api/bi")

@app.get("/api/health")
@app.get("/health")
def health():
    return {"status": "ok"}

if settings.frontend_dist and Path(settings.frontend_dist).is_dir():
    app.mount("/", StaticFiles(directory=settings.frontend_dist, html=True), name="frontend")
