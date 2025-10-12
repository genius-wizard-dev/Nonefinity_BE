from celery import Celery
from app.configs.settings import settings

# Create Celery app instance
celery_app = Celery(
    "ai_tasks_system",
    broker=(f"redis://:{settings.redis_password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
            if settings.redis_password else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"),
    backend=(f"redis://:{settings.redis_password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
             if settings.redis_password else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"),
)


__all__ = ["celery_app"]
