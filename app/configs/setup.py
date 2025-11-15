from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette import status
from scalar_fastapi import get_scalar_api_reference
from app.schemas.response import ApiError, ErrorDetail
from app.utils.api_response import JSONResponse
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.utils import setup_logging, get_logger
from app.middlewares import init_sentry
from app.databases import mongodb, init_instance_manager, shutdown_instance_manager
# Removed connection pooling imports as we no longer use them
from app.models import DOCUMENT_MODELS
from app.api import webhooks_router, auth_router, file_router, duckdb_router, dataset_router, credential_router, provider_router, embedding_router, model_router, tasks_router, knowledge_store, chat_router, google_router, intergrate_router, mcp_router, api_keys_router

logger = get_logger(__name__)


async def _setup_logging() -> None:
    """Setup application logging configuration"""
    setup_logging(
        level="DEBUG" if settings.APP_DEBUG else "INFO",
        app_name=settings.APP_NAME,
        enable_json=settings.APP_ENV == "prod",
        log_file="logs/app.log" if settings.APP_ENV == "prod" else None
    )
    logger.info("Logging configuration initialized")


async def _setup_sentry() -> None:
    """Setup Sentry monitoring for production environment"""
    if not settings.SENTRY_DSN:
        logger.warning("Sentry DSN not configured - monitoring disabled")
        return

    if settings.APP_ENV != "prod":
        logger.info("Sentry monitoring disabled - not in production environment")
        return

    try:
        init_sentry(
            dsn=settings.SENTRY_DSN,
            environment=settings.APP_ENV,
            release=settings.RELEASE,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            send_default_pii=settings.SENTRY_SEND_DEFAULT_PII
        )
        logger.info("Sentry monitoring initialized for production environment")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {str(e)}")
        # Don't raise exception for Sentry setup failure


async def _setup_databases() -> None:
    """Initialize database connections and extensions"""
    # Initialize MongoDB and Beanie
    try:
        await mongodb.connect(document_models=DOCUMENT_MODELS)
        logger.info("MongoDB connection established successfully")
    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {str(e)}")
        raise

    # Initialize Redis connection
    try:
        from app.services.redis_service import redis_service
        await redis_service.get_client()  # Test connection
        logger.info("Redis connection established successfully")
    except Exception as e:
        logger.error(f"Failed to initialize Redis: {str(e)}")
        # Don't raise - Redis is optional for basic functionality
        logger.warning("Redis caching will be disabled")

    # Initialize AI providers from YAML
    try:
        from app.services.provider_service import ProviderService
        count = await ProviderService.initialize_providers()
        logger.info(f"AI providers initialized successfully ({count} providers processed)")
    except Exception as e:
        logger.error(f"Failed to initialize AI providers: {str(e)}")
        # Don't raise - this is not critical for app startup

    # Initialize DuckDB instance manager
    try:
        init_instance_manager(
            instance_ttl=settings.DUCKDB_INSTANCE_TTL,
            cleanup_interval=settings.DUCKDB_CLEANUP_INTERVAL
        )
        logger.info("DuckDB instance manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DuckDB instance manager: {str(e)}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager"""
    logger.info("Starting Nonefinity Agent application...")

    try:
        # Setup components in order
        await _setup_logging()
        await _setup_sentry()
        await _setup_databases()

        logger.info("Application startup completed successfully")

        yield

    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        raise
    finally:
        # Cleanup resources
        logger.info("Shutting down Nonefinity Agent application...")
        try:
            await mongodb.disconnect()
            # Shutdown DuckDB instance manager
            await shutdown_instance_manager()
            # Close Redis connection
            try:
                from app.services.redis_service import redis_service
                await redis_service.close()
                logger.info("Redis connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {str(e)}")
            # No more connection pools to close - connections are created and closed per request
            logger.info("Application shutdown completed successfully")
        except Exception as e:
            logger.error(f"Error during shutdown: {str(e)}")


async def _handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Handle custom application errors"""
    errors = exc.errors or []
    if exc.field:
        errors.append({
            "code": exc.code,
            "message": exc.message,
            "field": exc.field
        })

    body = ApiError(
        success=False,
        message=exc.message,
        errors=[ErrorDetail(**e) for e in errors]
    ).model_dump(mode="json", exclude_none=True)

    return JSONResponse(content=body, status_code=exc.status_code)


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions from Starlette"""
    body = ApiError(
        success=False,
        message=str(exc.detail)
    ).model_dump(mode="json", exclude_none=True)

    return JSONResponse(content=body, status_code=exc.status_code)


async def _handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handle request validation errors"""
    errors = []
    for error in exc.errors():
        location = ".".join(
            str(x) for x in error.get("loc", [])
            if x not in ("body",)
        )
        errors.append({
            "code": error.get("type", "validation_error"),
            "message": error.get("msg", ""),
            "field": location or None
        })

    body = ApiError(
        success=False,
        message="Validation error",
        errors=[ErrorDetail(**e) for e in errors]
    ).model_dump(mode="json", exclude_none=True)

    return JSONResponse(
        content=body,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
    )


def install_cors_middleware(app: FastAPI) -> None:
    """Install CORS middleware for the application"""
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_CREDENTIALS,
        allow_methods=settings.CORS_METHODS,
        allow_headers=settings.CORS_HEADERS,
        expose_headers=settings.CORS_EXPOSE_HEADERS,
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Install all exception handlers for the application"""
    app.exception_handler(AppError)(_handle_app_error)
    app.exception_handler(StarletteHTTPException)(_handle_http_exception)
    app.exception_handler(RequestValidationError)(_handle_validation_error)

    logger.info("Exception handlers installed successfully")


def _create_api_prefix(endpoint_name: str) -> str:
    """Create API prefix for router endpoints"""
    return f"/api/v1/{endpoint_name}"


def include_routers(app: FastAPI) -> None:
    """Include all API routers with proper configuration"""
    routers_config = [
        (webhooks_router, "webhooks"),
        (file_router, "file"),
        (embedding_router, "embedding"),
        (tasks_router, "tasks"),
        (knowledge_store.router, "knowledge-stores"),
        (chat_router, "chats"),
        (api_keys_router, "api-keys"),
        (google_router, "google"),
        (intergrate_router, "intergrates"),
        (mcp_router, "mcp"),
        (dataset_router, "datasets"),
        (credential_router, "credentials"),
        (provider_router, "providers"),
        (model_router, "models"),
        (auth_router, "auth"),
        ]
    if settings.APP_ENV == "dev":
      routers_config.extend([
          (duckdb_router, "duckdb"),
      ])
      @app.get("/scalar", include_in_schema=False)
      async def scalar_html():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            scalar_proxy_url="https://proxy.scalar.com",
        )

    for router, prefix_name in routers_config:
        app.include_router(
            router,
            prefix=_create_api_prefix(prefix_name)
        )


    logger.info(f"Included {len(routers_config)} API routers successfully")


def create_app() -> FastAPI:
    """Create and configure FastAPI application with all components"""
    # Create FastAPI app with enhanced configuration
    app = FastAPI(
        title=settings.APP_NAME,
        description="Nonefinity Agent Backend API",
        version="1.0.0",
        debug=settings.APP_DEBUG,
        lifespan=lifespan,
        docs_url="/docs" if settings.APP_DEBUG else None,
        redoc_url="/redoc" if settings.APP_DEBUG else None,

    )


    # Install CORS middleware
    install_cors_middleware(app)

    # Install exception handlers
    install_exception_handlers(app)

    # Include API routers
    include_routers(app)

    logger.info("FastAPI application created and configured successfully")
    return app
