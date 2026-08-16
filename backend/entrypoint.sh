#!/bin/sh
set -e

echo "Running database migrations via Alembic..."
alembic upgrade head

echo "Starting YouTube Automation FastAPI Backend..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
