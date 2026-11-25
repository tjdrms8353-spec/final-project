# dayribbon backend — FastAPI + SQLite (TiDB 전환 시 DATABASE_URL만 교체)
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV DATABASE_URL=sqlite:////data/dayribbon.db \
    SEED_DEMO=0 \
    DEMO_EVENTS_ENABLED=0 \
    AUTO_ANALYSIS_INTERVAL_SEC=600

VOLUME /data
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
