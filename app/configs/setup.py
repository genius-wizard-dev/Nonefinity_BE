from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette import status

from app.schemas.response import ApiError, ErrorDetail
from app.utils.api_response import JSONResponse
from app.configs.settings import settings
from app.core.exceptions import AppError
from app.utils import setup_logging, get_logger
from app.middlewares import init_sentry
from app.databases import mongodb, init_duckdb_extensions
from app.models import DOCUMENT_MODELS
from app.api import webhooks_router, auth_router, file_router, dataset_router

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

    # Initialize DuckDB extensions
    try:
        init_duckdb_extensions()
        logger.info("DuckDB extensions initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DuckDB extensions: {str(e)}")
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
    ).model_dump(exclude_none=True)

    return JSONResponse(content=body, status_code=exc.status_code)


async def _handle_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handle HTTP exceptions from Starlette"""
    body = ApiError(
        success=False,
        message=str(exc.detail)
    ).model_dump(exclude_none=True)

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
    ).model_dump(exclude_none=True)

    return JSONResponse(
        content=body,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY
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
        (auth_router, "auth", ["Authentication"]),
        (webhooks_router, "webhooks", ["Webhooks"]),
        (file_router, "file", ["File Management"]),
        (dataset_router, "dataset", ["Dataset Management"])
    ]

    for router, prefix_name, tags in routers_config:
        app.include_router(
            router,
            prefix=_create_api_prefix(prefix_name),
            tags=tags
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

    # Install exception handlers
    install_exception_handlers(app)

    # Include API routers
    include_routers(app)

    logger.info("FastAPI application created and configured successfully")
    return app
