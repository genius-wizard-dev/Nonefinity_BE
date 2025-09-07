from contextlib import asynccontextmanager
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
from app.databases import mongodb
from app.models import DOCUMENT_MODELS
from app.api import webhooks_router, auth_router, file_router, folder_router

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
        logger.info(
            "Sentry monitoring disabled - not in production environment")
    else:
        logger.warning("Sentry DSN not configured - monitoring disabled")

    # Initialize MongoDB and Beanie
    try:
        await mongodb.connect(document_models=DOCUMENT_MODELS)


    except Exception as e:
        logger.error(f"Failed to initialize MongoDB: {str(e)}")
        raise

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down Nonefinity Agent application...")
    await mongodb.disconnect()


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        errors = exc.errors or []
        if exc.field:
            errors.append({"code": exc.code, "message": exc.message, "field": exc.field})
        body = ApiError(success=False, message=exc.message, errors=[ErrorDetail(**e) for e in errors]).model_dump(exclude_none=True)
        return JSONResponse(content=body, status_code=exc.status_code)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        body = ApiError(success=False, message=str(exc.detail)).model_dump(exclude_none=True)
        return JSONResponse(content=body, status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errs = []
        for e in exc.errors():
            loc = ".".join(str(x) for x in e.get("loc", []) if x not in ("body",))
            errs.append({"code": e.get("type", "validation_error"), "message": e.get("msg", ""), "field": loc or None})
        body = ApiError(success=False, message="Validation error", errors=[ErrorDetail(**e) for e in errs]).model_dump(exclude_none=True)
        return JSONResponse(content=body, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


def _create_api_prefix(app_name: str) -> str:
    return f"/api/v1/{app_name}"

def include_routers(app: FastAPI) -> None:
    """Include all API routers"""

    app.include_router(auth_router, prefix=_create_api_prefix("auth"), tags=["Auth"])
    app.include_router(webhooks_router, prefix=_create_api_prefix("webhooks"), tags=["Webhooks"])
    app.include_router(file_router, prefix=_create_api_prefix("file"), tags=["File"])
    app.include_router(folder_router, prefix=_create_api_prefix("folder"), tags=["Folder"])


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    # Create FastAPI app
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.APP_DEBUG,
        lifespan=lifespan
    )

    # Include exceptions handler
    install_exception_handlers(app)

    # Include routers
    include_routers(app)

    return app
