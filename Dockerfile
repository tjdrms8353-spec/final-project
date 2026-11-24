# syntax=docker/dockerfile:1
# dayribbon: React frontend build + FastAPI backend in one container.
# The backend serves the built frontend (FRONTEND_DIST) and the /api routes.

FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ARG VITE_DEMO_MODE=1
ENV VITE_DEMO_MODE=$VITE_DEMO_MODE
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /workspace/backend
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY backend/alembic.ini ./alembic.ini
COPY migrations /workspace/migrations
COPY --from=frontend /build/dist /workspace/frontend-dist
ENV FRONTEND_DIST=/workspace/frontend-dist
EXPOSE 8001
# Apply DB migrations, seed demo data (idempotent), then serve.
CMD ["sh", "-c", "alembic upgrade head && python -m app.features.bi.demo_seed; uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
