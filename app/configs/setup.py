from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.configs.settings import settings
from app.utils import setup_logging, get_logger
from app.middlewares import init_sentry
from app.databases import mongodb
from app.models import DOCUMENT_MODELS
from app.services import mongodb_service
from app.api import mongodb_router

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info("Starting Nonefinity Agent application...")
    
    # Setup logging
    setup_logging(
        level="DEBUG" if settings.APP_DEBUG else "INFO",
        app_name=settings.APP_NAME,
        enable_json=settings.APP_ENV == "prod",
        log_file="logs/app.log" if settings.APP_ENV == "prod" else None
    )
    
    # Initialize Sentry monitoring (only in production environment)
    if settings.SENTRY_DSN and settings.APP_ENV == "prod":
        init_sentry(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            release=settings.RELEASE,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=settings.SENTRY_SEND_DEFAULT_PII
        )
        logger.info("Sentry monitoring initialized for production environment")
    elif settings.APP_ENV != "prod":
        logger.info("Sentry monitoring disabled - not in production environment")
    else:
        logger.warning("Sentry DSN not configured - monitoring disabled")
    
    # Initialize MongoDB and Beanie
    try:
        await mongodb.connect(document_models=DOCUMENT_MODELS)
        
        # Initialize MongoDB service
        await mongodb_service.initialize()
        
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {str(e)}")
        raise
    
    logger.info("Application started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Nonefinity Agent application...")
    await mongodb.disconnect()
    
def _create_api_prefix(app_name: str) -> str:
    return f"/api/v1/{app_name}"

def include_routers(app: FastAPI) -> None:
    """Include all API routers"""
    
    # Only include MongoDB router in development environment with debug enabled
    if settings.APP_ENV == "dev" and settings.APP_DEBUG:
        app.include_router(mongodb_router, prefix=_create_api_prefix("mongodb"))
        logger.info("MongoDB router included (dev mode with debug enabled)")

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.APP_DEBUG,
        lifespan=lifespan
    )
    
    # Include routers
    include_routers(app)
    
    # Add basic endpoints
    @app.get("/")
    def read_root():
        logger.info("Root endpoint accessed")
        return {"message": "Hello World", "app": settings.APP_NAME}

    @app.get("/health")
    def health_check():
        logger.info("Health check endpoint accessed")
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "environment": settings.APP_ENV
        }
    
    return app
