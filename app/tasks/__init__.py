from celery import Celery
from app.configs.settings import settings


celery_app = Celery(
    "ai_tasks_system",
    broker=(f"redis://:{settings.redis_password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
            if settings.redis_password else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"),
    backend=(f"redis://:{settings.redis_password}@{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"
             if settings.redis_password else f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"),
    include=[
        'app.tasks.chat_tasks',
        'app.tasks.embedding_tasks',
        'app.tasks.chat.export_history',
    ]
)

celery_app.conf.update(
    task_serializer=settings.CELERY_TASK_SERIALIZER,
    accept_content=settings.CELERY_ACCEPT_CONTENT,
    result_serializer=settings.CELERY_RESULT_SERIALIZER,
    timezone=settings.CELERY_TIMEZONE,
    enable_utc=settings.CELERY_ENABLE_UTC,
    result_expires=3600,
    task_ignore_result=False,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    task_default_queue='chats',  # Everything goes to 'chats' by default
    task_routes={
        'tasks.embedding.run_embedding': {'queue': 'embeddings'},
        'tasks.embedding.run_text_embedding': {'queue': 'embeddings'},
        'tasks.embedding.search_similar': {'queue': 'embeddings'},
        'tasks.chat.export_history': {'queue': 'chats'},
    },
)


# Import tasks to ensure they are registered
# Note: We import inside the module or rely on 'include' in worker command,
# but importing here ensures the app knows about them if imported elsewhere.
# However, to avoid circular imports, we might rely on the worker 'include' argument.


# Signal handlers for Database Initialization
from celery.signals import worker_process_init, worker_ready
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.configs.settings import settings
from app.models import DOCUMENT_MODELS
from app.utils import get_logger

logger = get_logger(__name__)

async def _init_db():
    """Initialize MongoDB connection and Beanie ODM"""
    try:
        # Create Motor Client
        client = AsyncIOMotorClient(
            settings.MONGO_URL,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000,
            socketTimeoutMS=10000,
            maxPoolSize=50,
            minPoolSize=0,
        )

        # Initialize Beanie
        database = client[settings.MONGO_DB]
        await init_beanie(
            database=database,
            document_models=DOCUMENT_MODELS
        )
        logger.info("MongoDB/Beanie initialized for Celery process")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB/Beanie: {e}")
        # Don't raise here to allow worker to continue potentially without DB
        # But for critical tasks it might fail later

def run_async_init(**kwargs):
    """Helper to run async init in sync signal handler"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_init_db())

@worker_process_init.connect
def init_worker_process(**kwargs):
    """Initialize DB when a worker child process starts"""
    logger.info("Initializing worker process...")
    run_async_init()

@worker_ready.connect
def init_main_process(**kwargs):
    """Initialize DB when the main worker is ready (for MainProcess tasks)"""
    logger.info("Initializing main process...")
    run_async_init()

__all__ = ["celery_app"]
