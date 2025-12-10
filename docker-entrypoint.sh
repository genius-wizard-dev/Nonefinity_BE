#!/bin/bash
set -e

# Start Unified Celery Worker (Queues: chats, embeddings)
echo "Starting Unified Celery Worker (Queues: chats, embeddings)..."
uv run celery -A app.tasks:celery_app worker -Q chats,embeddings -l info --pool=prefork --include app.tasks.chat_tasks,app.tasks.embedding_tasks &

# Wait a moment for Celery to start
sleep 2

# Start Uvicorn in foreground (this keeps the container alive)
echo "Starting Uvicorn server..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

