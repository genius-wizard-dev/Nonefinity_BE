from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from app.configs.settings import settings
from app.utils import get_logger

logger = get_logger(__name__)


def _is_ngrok_domain(origin: str) -> bool:
    """Check if origin is an ngrok domain"""
    ngrok_patterns = [
        ".ngrok-free.app",
        ".ngrok.io",
        ".ngrok.app",
    ]
    return any(pattern in origin for pattern in ngrok_patterns)


def _is_allowed_origin(origin: str) -> bool:
    """Check if origin is allowed"""
    # Check configured origins
    if origin in settings.CORS_ORIGINS:
        return True

    # In dev mode, allow ngrok domains
    if settings.APP_ENV == "dev" and _is_ngrok_domain(origin):
        return True

    return False


class CustomCORSMiddleware(BaseHTTPMiddleware):
    """Custom CORS middleware that supports dynamic origins (e.g., ngrok)"""

    async def dispatch(self, request: Request, call_next: ASGIApp) -> Response:
        origin = request.headers.get("origin")

        # Handle preflight requests
        if request.method == "OPTIONS":
            response = Response()
            if origin and _is_allowed_origin(origin):
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                # Handle wildcard methods/headers
                methods = settings.CORS_METHODS
                if "*" in methods:
                    response.headers["Access-Control-Allow-Methods"] = "*"
                else:
                    response.headers["Access-Control-Allow-Methods"] = ", ".join(methods)

                headers = settings.CORS_HEADERS
                if "*" in headers:
                    response.headers["Access-Control-Allow-Headers"] = "*"
                else:
                    response.headers["Access-Control-Allow-Headers"] = ", ".join(headers)
                response.headers["Access-Control-Max-Age"] = "3600"
            return response

        # Handle actual requests
        response = await call_next(request)

        if origin and _is_allowed_origin(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response

