from fastapi import FastAPI
from app.features.trends.router import router as trends_router
from app.features.finance.router import router as finance_router
from app.features.receipts.router import router as receipts_router

app = FastAPI(title="Final Project API")
for router in (trends_router, finance_router, receipts_router):
    app.include_router(router, prefix="/api/v1")

@app.get("/api/health")
def health():
    return {"status": "ok"}
