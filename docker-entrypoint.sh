#!/bin/bash
set -e

# Start Celery worker in background
echo "Starting Celery worker..."
uv run celery -A app.tasks.embedding_tasks:celery_app worker -Q embeddings -l info --pool=prefork &

# Wait a moment for Celery to start
sleep 2

# Start Uvicorn in foreground (this keeps the container alive)
echo "Starting Uvicorn server..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

